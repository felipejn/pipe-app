"""Servicos da Meteorologia — Etapas A (Localizacao) e B (Previsao).

Funcoes puras (sem Flask): recebem dados simples e devolvem dados
simples, para futura reutilizacao pelo Assistente. A cache da ultima
previsao e o unico ponto que toca o BD — e opcional (best-effort) e
esta isolado das funcoes puras.
"""
from datetime import datetime, timedelta, timezone
import os

import json
import logging

import requests

GEOCODING_URL = 'https://api.openweathermap.org/geo/1.0/direct'
WEATHER_URL = 'https://api.openweathermap.org/data/2.5/weather'
FORECAST_5DAY_URL = 'https://api.openweathermap.org/data/2.5/forecast'
USER_AGENT = 'PIPE-Meteorologia/1.0'
TIMEOUT_SEGUNDOS = 8
TIMEZONE_PREDEFINIDO = 'Europe/Lisbon'
PAISES_PT = {'PT': 'Portugal'}


def _openweather_api_key():
    try:
        from flask import current_app, has_app_context
        if has_app_context():
            return current_app.config.get('OPENWEATHER_API_KEY') or os.environ.get(
                'OPENWEATHER_API_KEY')
    except ImportError:
        pass
    return os.environ.get('OPENWEATHER_API_KEY')

# Cache da ultima previsao com sucesso (fallback quando a API falha).
# Uma linha por coordenadas arredondadas (~1 km); payload em JSON no
# formato devolvido por obter_previsao. IDADE_MAXIMA limita o que se
# serve como "guardado": passado esse prazo, sao dados que ja nao
# descrevem o presente (temperatura atual / horaria) e o utilizador
# fica melhor servido com a mensagem de indisponivel. VIDA_LIMPA limita
# quantas localizacoes sao guardadas (limpeza oportuna na escrita).
IDADE_MAXIMA_CACHE_HORAS = 24
VIDA_LIMPA_CACHE_DIAS = 30

TETO_NOME = 120
TETO_PAIS = 80
TETO_REGIAO = 120
TETO_TIMEZONE = 64


def pesquisar_locais(q):
    """Pesquisa locais na API Geocoding da OpenWeather.

    Devolve lista normalizada [{nome, latitude, longitude, pais, regiao,
    detalhe, timezone}], [] se pesquisa invalida/sem resultados,
    ou None se a API falhar (timeout/rede/HTTP).
    """
    texto = (q or '').strip()
    if len(texto) < 2 or len(texto) > 100:
        return []
    chave = _openweather_api_key()
    if not chave:
        return None
    try:
        resposta = requests.get(
            GEOCODING_URL,
            params={'q': texto, 'limit': 5, 'appid': chave},
            timeout=TIMEOUT_SEGUNDOS,
            headers={'User-Agent': USER_AGENT},
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except Exception:
        return None
    resultados = dados if isinstance(dados, list) else []
    locais = []
    for item in resultados:
        try:
            locais.append({
                'nome': (item.get('local_names') or {}).get('pt')
                        or item.get('name'),
                'latitude': item.get('lat'),
                'longitude': item.get('lon'),
                'pais': PAISES_PT.get(item.get('country'), item.get('country')),
                'regiao': item.get('state'),
                'detalhe': None,
                'timezone': item.get('timezone') or TIMEZONE_PREDEFINIDO,
            })
        except Exception:
            continue
    return locais


def _texto_valido(valor, teto):
    return (isinstance(valor, str) and valor.strip()
            and len(valor.strip()) <= teto)


def validar_payload_localizacao(payload):
    """Valida o payload de gravacao. Devolve (limpo, erro)."""
    if not isinstance(payload, dict):
        return None, 'Dados inválidos.'
    try:
        lat = float(payload.get('latitude'))
        lon = float(payload.get('longitude'))
    except (TypeError, ValueError):
        return None, 'Coordenadas inválidas.'
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None, 'Coordenadas fora de intervalo.'
    if not _texto_valido(payload.get('nome'), TETO_NOME):
        return None, 'Nome inválido.'
    if not _texto_valido(payload.get('pais'), TETO_PAIS):
        return None, 'País inválido.'
    regiao = payload.get('regiao')
    if regiao is not None and regiao != '':
        if not _texto_valido(regiao, TETO_REGIAO):
            return None, 'Região inválida.'
        regiao = regiao.strip()
    else:
        regiao = None
    timezone = payload.get('timezone') or TIMEZONE_PREDEFINIDO
    if not _texto_valido(timezone, TETO_TIMEZONE):
        return None, 'Timezone inválido.'
    return {
        'nome': payload.get('nome').strip(),
        'latitude': lat,
        'longitude': lon,
        'pais': payload.get('pais').strip(),
        'regiao': regiao,
        'timezone': timezone.strip(),
    }, None


def guardar_localizacao(user_id, payload):
    """Cria ou actualiza a localizacao do utilizador. (ok, erro)."""
    from app import db
    from app.meteorologia.models import LocalizacaoMeteorologia

    limpo, erro = validar_payload_localizacao(payload)
    if erro:
        return False, erro
    try:
        linha = LocalizacaoMeteorologia.query.filter_by(
            user_id=user_id).first()
        if linha is None:
            linha = LocalizacaoMeteorologia(user_id=user_id, **limpo)
            db.session.add(linha)
        else:
            for chave, valor in limpo.items():
                setattr(linha, chave, valor)
        db.session.commit()
        return True, None
    except Exception:
        db.session.rollback()
        return False, 'Não foi possível guardar a localização.'

# ── Etapa B — WMO e vento ──

# (descricao PT-PT, emoji) por codigo WMO — sem dependencias.
MAPA_WMO = {
    0: ('Céu limpo', '☀️'),
    1: ('Quase limpo', '🌤️'),
    2: ('Parcialmente nublado', '⛅'),
    3: ('Encoberto', '☁️'),
    45: ('Nevoeiro', '🌫️'),
    48: ('Nevoeiro com geada', '🌫️'),
    51: ('Chuvisco fraco', '🌦️'),
    53: ('Chuvisco', '🌦️'),
    55: ('Chuvisco forte', '🌧️'),
    56: ('Chuvisco gelado fraco', '🌧️'),
    57: ('Chuvisco gelado', '🌧️'),
    61: ('Chuva fraca', '🌦️'),
    63: ('Chuva', '🌧️'),
    65: ('Chuva forte', '🌧️'),
    66: ('Chuva gelada fraca', '🌧️'),
    67: ('Chuva gelada', '🌧️'),
    71: ('Neve fraca', '🌨️'),
    73: ('Neve', '🌨️'),
    75: ('Neve forte', '❄️'),
    77: ('Granizo', '🌨️'),
    80: ('Aguaceiros fracos', '🌦️'),
    81: ('Aguaceiros', '🌧️'),
    82: ('Aguaceiros fortes', '🌧️'),
    85: ('Aguaceiros de neve', '🌨️'),
    86: ('Aguaceiros de neve fortes', '❄️'),
    95: ('Trovoada', '⛈️'),
    96: ('Trovoada com granizo fraco', '⛈️'),
    99: ('Trovoada com granizo', '⛈️'),
}

PONTOS_CARDEAIS = (
    'Norte', 'Nordeste', 'Este', 'Sudeste',
    'Sul', 'Sudoeste', 'Oeste', 'Noroeste',
)


def descrever_wmo(codigo):
    """(descricao PT-PT, emoji) para um codigo WMO; fallback ('—', '❔')."""
    try:
        return MAPA_WMO.get(int(codigo), ('—', '❔'))
    except (TypeError, ValueError):
        return ('—', '❔')


def direcao_cardinal(graus):
    """Converte graus (0–360) em ponto cardeal por extenso."""
    try:
        valor = float(graus) % 360
    except (TypeError, ValueError):
        return '—'
    return PONTOS_CARDEAIS[int((valor + 22.5) // 45) % 8]



# ── Etapa B — Previsão OpenWeather ──

MAPA_OPENWEATHER = {
    200: ('Trovoada com chuva fraca', '⛈️'),
    201: ('Trovoada com chuva', '⛈️'),
    202: ('Trovoada com chuva forte', '⛈️'),
    210: ('Trovoada fraca', '⛈️'), 211: ('Trovoada', '⛈️'),
    212: ('Trovoada forte', '⛈️'), 221: ('Trovoada irregular', '⛈️'),
    230: ('Trovoada com chuvisco fraco', '⛈️'),
    231: ('Trovoada com chuvisco', '⛈️'),
    232: ('Trovoada com chuvisco forte', '⛈️'),
    300: ('Chuvisco fraco', '🌦️'), 301: ('Chuvisco', '🌦️'),
    302: ('Chuvisco forte', '🌧️'), 310: ('Chuva fraca', '🌦️'),
    311: ('Chuva', '🌧️'), 312: ('Chuva forte', '🌧️'),
    313: ('Aguaceiros', '🌧️'), 314: ('Aguaceiros fortes', '🌧️'),
    321: ('Aguaceiros', '🌧️'),
    500: ('Chuva fraca', '🌦️'), 501: ('Chuva moderada', '🌧️'),
    502: ('Chuva forte', '🌧️'), 503: ('Chuva muito forte', '🌧️'),
    504: ('Chuva extrema', '🌧️'), 511: ('Chuva gelada', '🌧️'),
    520: ('Aguaceiros fracos', '🌦️'), 521: ('Aguaceiros', '🌧️'),
    522: ('Aguaceiros fortes', '🌧️'), 531: ('Aguaceiros irregulares', '🌧️'),
    600: ('Neve fraca', '🌨️'), 601: ('Neve', '🌨️'),
    602: ('Neve forte', '❄️'), 611: ('Granizo e neve', '🌨️'),
    612: ('Aguaceiros de neve fracos', '🌨️'),
    613: ('Aguaceiros de neve', '🌨️'), 615: ('Chuva e neve fracas', '🌨️'),
    616: ('Chuva e neve', '🌨️'), 620: ('Aguaceiros de neve fracos', '🌨️'),
    621: ('Aguaceiros de neve', '🌨️'), 622: ('Aguaceiros de neve fortes', '❄️'),
    701: ('Nevoeiro', '🌫️'), 711: ('Fumo', '🌫️'), 721: ('Bruma', '🌫️'),
    731: ('Redemoinhos de areia', '🌪️'), 741: ('Nevoeiro', '🌫️'),
    751: ('Areia', '🌫️'), 761: ('Poeira', '🌫️'), 762: ('Cinzas vulcânicas', '🌫️'),
    771: ('Rajadas de vento', '💨'), 781: ('Tornado', '🌪️'),
    800: ('Céu limpo', '☀️'), 801: ('Poucas nuvens', '🌤️'),
    802: ('Nuvens dispersas', '⛅'), 803: ('Nuvens fragmentadas', '☁️'),
    804: ('Encoberto', '☁️'),
}


def descrever_openweather(codigo):
    try:
        return MAPA_OPENWEATHER.get(int(codigo), ('—', '❔'))
    except (TypeError, ValueError):
        return ('—', '❔')


def _coordenadas_validas(lat, lon):
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def _num(valor):
    try:
        if valor is None or isinstance(valor, bool):
            return None
        return float(valor)
    except (TypeError, ValueError):
        return None


def obter_previsao(lat, lon):
    """Previsão OpenWeather normalizada para coordenadas ou None se falhar.

    Com a API em baixo, serve a ultima previsao guardada (ate
    IDADE_MAXIMA_CACHE_HORAS) com de_cache=True; sem cache valida,
    devolve None. A escrita/leitura da cache e best-effort: qualquer
    falha (BD indisponivel, sem app context) nunca afecta o resultado.
    """
    coords = _coordenadas_validas(lat, lon)
    if coords is None:
        return None
    lat, lon = coords
    chave = _openweather_api_key()
    if not chave:
        return _servir_cache_ou_none(lat, lon)
    try:
        params = {'lat': lat, 'lon': lon, 'appid': chave,
                  'units': 'metric', 'lang': 'pt'}
        resposta_atual = requests.get(
            WEATHER_URL, params=params, timeout=TIMEOUT_SEGUNDOS,
            headers={'User-Agent': USER_AGENT})
        resposta_atual.raise_for_status()
        atual_api = resposta_atual.json()
        resposta_forecast = requests.get(
            FORECAST_5DAY_URL, params=params, timeout=TIMEOUT_SEGUNDOS,
            headers={'User-Agent': USER_AGENT})
        resposta_forecast.raise_for_status()
        dados = resposta_forecast.json()
    except Exception:
        return _servir_cache_ou_none(lat, lon)
    try:
        if not isinstance(atual_api, dict) or not atual_api:
            return None
        if not isinstance(dados, dict) or not isinstance(dados.get('list'), list):
            return None
        main = atual_api.get('main') or {}
        vento_api = atual_api.get('wind') or {}
        weather = (atual_api.get('weather') or [{}])[0]
        offset = int(atual_api.get('timezone', dados.get('city', {}).get('timezone', 0)))
        timezone_nome = _timezone_offset(offset)
        agora_epoch = _num(atual_api.get('dt'))
        if agora_epoch is None:
            return None
        agora_local = datetime.fromtimestamp(
            agora_epoch + offset, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M')
        codigo_int = int(weather['id']) if weather.get('id') is not None else None
        descricao, emoji = descrever_openweather(codigo_int)
        graus = _num(vento_api.get('deg'))
        entradas = sorted(
            (item for item in dados['list'] if isinstance(item, dict)
             and _num(item.get('dt')) is not None),
            key=lambda item: float(item['dt']))
        proxima = next((item for item in entradas
                        if float(item['dt']) >= agora_epoch), None)
        pop_atual = _num(proxima.get('pop')) if proxima else None
        if pop_atual is not None:
            pop_atual *= 100
        precip_atual = sum(_num((atual_api.get(k) or {}).get('1h')) or 0
                           for k in ('rain', 'snow'))
        atual = {
            'hora': agora_local,
            'temperatura': _num(main.get('temp')),
            'sensacao_termica': _num(main.get('feels_like')),
            'humidade': _num(main.get('humidity')),
            'precipitacao': precip_atual,
            'probabilidade_precipitacao': pop_atual,
            'codigo_wmo': codigo_int,
            'vento_velocidade': (round(_num(vento_api.get('speed')) * 3.6)
                                 if _num(vento_api.get('speed')) is not None else None),
            'vento_direcao_graus': graus,
            'uv': _num(atual_api.get('uvi')),
            'temp_max_hoje': _num(main.get('temp_max')),
            'temp_min_hoje': _num(main.get('temp_min')),
            'descricao_pt': descricao,
            'emoji': emoji,
            'vento_direcao_cardinal': direcao_cardinal(graus),
        }
        horaria = []
        limite_horas = agora_epoch + 24 * 60 * 60
        for item in entradas:
            dt = float(item['dt'])
            if dt < agora_epoch or dt > limite_horas:
                continue
            main_item = item.get('main') or {}
            condicao = (item.get('weather') or [{}])[0]
            cod_h = int(condicao['id']) if condicao.get('id') is not None else None
            chuva = sum(_num((item.get(k) or {}).get('3h')) or 0
                        for k in ('rain', 'snow'))
            pop = _num(item.get('pop'))
            if pop is not None:
                pop *= 100
            horaria.append({
                'hora': item.get('dt_txt', '').replace(' ', 'T')[:16],
                'temperatura': _num(main_item.get('temp')),
                'codigo_wmo': cod_h,
                'descricao_pt': descrever_openweather(cod_h)[0],
                'emoji': descrever_openweather(cod_h)[1],
                'prob_precipitacao': pop,
                'precipitacao': chuva,
            })
        grupos = {}
        for item in entradas:
            data_local = str(item.get('dt_txt') or '')[:10]
            if len(data_local) != 10:
                continue
            grupo = grupos.setdefault(data_local, [])
            grupo.append(item)
        diaria = []
        for data_local, itens in list(sorted(grupos.items()))[:5]:
            temps = [_num((item.get('main') or {}).get('temp'))
                     for item in itens]
            temps = [t for t in temps if t is not None]
            condicoes = [((item.get('weather') or [{}])[0].get('id'))
                         for item in itens]
            contagem = {}
            for codigo in condicoes:
                if codigo is not None:
                    contagem[codigo] = contagem.get(codigo, 0) + 1
            cod_d = max(contagem, key=contagem.get) if contagem else None
            probs = [_num(item.get('pop')) for item in itens]
            probs = [p for p in probs if p is not None]
            precipitacao = sum(
                sum(_num((item.get(k) or {}).get('3h')) or 0
                    for k in ('rain', 'snow')) for item in itens)
            diaria.append({
                'data': data_local,
                'codigo_wmo': cod_d,
                'descricao_pt': descrever_openweather(cod_d)[0],
                'emoji': descrever_openweather(cod_d)[1],
                'temp_max': max(temps) if temps else None,
                'temp_min': min(temps) if temps else None,
                'prob_precipitacao': max(probs) * 100 if probs else None,
                'precipitacao': precipitacao,
            })
        resumo_hoje = next((dia for dia in diaria
                            if dia['data'] == agora_local[:10]), None)
        if resumo_hoje:
            atual['temp_max_hoje'] = resumo_hoje['temp_max']
            atual['temp_min_hoje'] = resumo_hoje['temp_min']
        payload = {
            'atual': atual,
            'horaria': horaria,
            'diaria': diaria,
            'timezone': timezone_nome,
            'atualizada_em': datetime.utcnow().strftime('%Y-%m-%dT%H:%M'),
            'fonte': 'OpenWeather',
        }
    except Exception:
        return _servir_cache_ou_none(lat, lon)

    _gravar_previsao_cache(lat, lon, payload)
    return payload


def _timezone_offset(offset):
    sinal = '+' if offset >= 0 else '-'
    minutos = abs(int(offset)) // 60
    return f'UTC{sinal}{minutos // 60:02d}:{minutos % 60:02d}'


def _gravar_previsao_cache(lat, lon, payload):
    """Grava a previsao actualizada na cache (best-effort).

    Usa begin_nested + IntegrityError para recuperar de corrida entre
    dois pedidos a gravar a mesma chave; rollback em qualquer falha.
    """
    from datetime import datetime, timedelta

    from flask import has_app_context
    from sqlalchemy.exc import IntegrityError

    if not has_app_context():
        return
    from app import db
    from app.meteorologia.models import PrevisaoCache

    chave = f'{lat:.2f},{lon:.2f}'
    try:
        with db.session.begin_nested():
            linha = PrevisaoCache.query.filter_by(chave=chave).first()
            if linha is None:
                linha = PrevisaoCache(chave=chave)
                db.session.add(linha)
            linha.payload = json.dumps(payload)
            linha.obtida_em = datetime.utcnow()
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    except Exception:
        db.session.rollback()
        logging.getLogger(__name__).warning(
            'Falha ao gravar cache de previsao para %s', chave, exc_info=True)
    finally:
        # Limpeza oportuna: remove linhas velhas para a tabela nao crescer.
        try:
            limite = datetime.utcnow() - timedelta(days=VIDA_LIMPA_CACHE_DIAS)
            PrevisaoCache.query.filter(
                PrevisaoCache.obtida_em < limite).delete(
                synchronize_session=False)
            db.session.commit()
        except Exception:
            db.session.rollback()


def _servir_cache_ou_none(lat, lon):
    """Devolve a previsao guardada (ate IDADE_MAXIMA) ou None.

    Marca o resultado com de_cache=True e obtida_em (timestamp da
    ultima gravacao com sucesso), para a UI e o Assistente avisarem
    da frescura.
    """
    from datetime import timedelta

    from flask import has_app_context

    if not has_app_context():
        return None
    from app import db
    from app.meteorologia.models import PrevisaoCache

    chave = f'{lat:.2f},{lon:.2f}'
    try:
        linha = PrevisaoCache.query.filter_by(chave=chave).first()
        if linha is None:
            return None
        idade = datetime.utcnow() - linha.obtida_em
        if idade > timedelta(hours=IDADE_MAXIMA_CACHE_HORAS):
            return None
        payload = json.loads(linha.payload)
    except Exception:
        logging.getLogger(__name__).warning(
            'Falha ao ler cache de previsao para %s', chave, exc_info=True)
        return None
    return dict(payload, de_cache=True, obtida_em=linha.obtida_em)


def obter_previsao_utilizador(user_id):
    """(payload | None, motivo) para a localizacao guardada do utilizador."""
    from app.meteorologia.models import LocalizacaoMeteorologia
    try:
        local = LocalizacaoMeteorologia.query.filter_by(
            user_id=user_id).first()
    except Exception:
        return None, 'api_indisponivel'
    if local is None:
        return None, 'sem_localizacao'
    previsao = obter_previsao(local.latitude, local.longitude)
    if previsao is None:
        return None, 'api_indisponivel'
    return previsao, 'ok'
