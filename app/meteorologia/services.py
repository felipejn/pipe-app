"""Servicos da Meteorologia — Etapas A (Localizacao) e B (Previsao).

Funcoes puras (sem Flask): recebem dados simples e devolvem dados
simples, para futura reutilizacao pelo Assistente.
"""
from datetime import datetime

import requests

GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
USER_AGENT = 'PIPE-Meteorologia/1.0'
TIMEOUT_SEGUNDOS = 8
TIMEZONE_PREDEFINIDO = 'Europe/Lisbon'

# Gancho de cache (V1: sem cache — todo o acesso a Forecast API fica
# dentro de obter_previsao, assinatura estavel (lat, lon); evolucao
# futura = wrapper interno com dict + TTL, sem tocar rotas/templates).

TETO_NOME = 120
TETO_PAIS = 80
TETO_REGIAO = 120
TETO_TIMEZONE = 64


def pesquisar_locais(q):
    """Pesquisa locais na API Geocoding da Open-Meteo.

    Devolve lista normalizada [{nome, latitude, longitude, pais, regiao,
    detalhe, timezone}], [] se pesquisa invalida/sem resultados,
    ou None se a API falhar (timeout/rede/HTTP).
    """
    texto = (q or '').strip()
    if len(texto) < 2 or len(texto) > 100:
        return []
    try:
        resposta = requests.get(
            GEOCODING_URL,
            params={'name': texto, 'count': 5,
                    'language': 'pt', 'format': 'json'},
            timeout=TIMEOUT_SEGUNDOS,
            headers={'User-Agent': USER_AGENT},
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except Exception:
        return None
    resultados = dados.get('results', []) or []
    locais = []
    for item in resultados:
        try:
            locais.append({
                'nome': item.get('name'),
                'latitude': item.get('latitude'),
                'longitude': item.get('longitude'),
                'pais': item.get('country'),
                'regiao': item.get('admin1'),
                'detalhe': item.get('admin2'),
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



# ── Etapa B — Previsão ──

PARAMS_FORECAST = {
    'current': ('temperature_2m,relative_humidity_2m,apparent_temperature,'
                'precipitation,weather_code,wind_speed_10m,'
                'wind_direction_10m,uv_index'),
    'hourly': 'temperature_2m,weather_code,precipitation_probability',
    'daily': ('weather_code,temperature_2m_max,temperature_2m_min,'
              'precipitation_probability_max'),
    'timezone': 'auto',
    'forecast_days': 7,
}


def _coordenadas_validas(lat, lon):
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def _indice_hora_atual(hora_atual, horas):
    """Indice em hourly.time da hora de current.time (fallback: >=; None)."""
    if not hora_atual or not horas:
        return None
    alvo = str(hora_atual)[:13]
    for i, h in enumerate(horas):
        if str(h)[:13] == alvo:
            return i
    for i, h in enumerate(horas):
        if str(h) >= str(hora_atual):
            return i
    return None


def _num(valor):
    try:
        if valor is None or isinstance(valor, bool):
            return None
        return float(valor)
    except (TypeError, ValueError):
        return None


def _wmo_seguro(lista, i):
    if i >= len(lista):
        return None
    try:
        return int(lista[i]) if lista[i] is not None else None
    except (TypeError, ValueError):
        return None


def _campo_compat(dados, nome_documentado, nome_antigo):
    """Lê o nome actual da API ou o nome antigo usado por respostas existentes."""
    return dados.get(nome_documentado, dados.get(nome_antigo))


def obter_previsao(lat, lon):
    """Previsao normalizada para (lat, lon) ou None se a API falhar."""
    coords = _coordenadas_validas(lat, lon)
    if coords is None:
        return None
    lat, lon = coords
    try:
        resposta = requests.get(
            FORECAST_URL,
            params={'latitude': lat, 'longitude': lon, **PARAMS_FORECAST},
            timeout=TIMEOUT_SEGUNDOS,
            headers={'User-Agent': USER_AGENT},
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except Exception:
        return None
    try:
        atual_api = dados.get('current') or {}
        if not isinstance(atual_api, dict) or not atual_api:
            return None
        horaria_api = dados.get('hourly') or {}
        diaria_api = dados.get('daily') or {}
        horas = horaria_api.get('time') or []
        probs = horaria_api.get('precipitation_probability') or []
        temps_h = horaria_api.get('temperature_2m') or []
        wmos_h = _campo_compat(horaria_api, 'weather_code', 'weathercode') or []
        idx = _indice_hora_atual(atual_api.get('time'), horas)
        prob_atual = None
        if idx is not None and idx < len(probs):
            prob_atual = _num(probs[idx])
        max_hoje = (diaria_api.get('temperature_2m_max') or [None])[0]
        min_hoje = (diaria_api.get('temperature_2m_min') or [None])[0]
        codigo = _campo_compat(atual_api, 'weather_code', 'weathercode')
        try:
            codigo_int = int(codigo) if codigo is not None else None
        except (TypeError, ValueError):
            codigo_int = None
        descricao, emoji = descrever_wmo(codigo_int)
        graus = _num(atual_api.get('wind_direction_10m'))
        atual = {
            'hora': atual_api.get('time'),
            'temperatura': _num(atual_api.get('temperature_2m')),
            'sensacao_termica': _num(atual_api.get('apparent_temperature')),
            'humidade': _num(atual_api.get('relative_humidity_2m')),
            'precipitacao': _num(atual_api.get('precipitation')),
            'probabilidade_precipitacao': prob_atual,
            'codigo_wmo': codigo_int,
            'vento_velocidade': _num(atual_api.get('wind_speed_10m')),
            'vento_direcao_graus': graus,
            'uv': _num(atual_api.get('uv_index')),
            'temp_max_hoje': _num(max_hoje),
            'temp_min_hoje': _num(min_hoje),
            'descricao_pt': descricao,
            'emoji': emoji,
            'vento_direcao_cardinal': direcao_cardinal(graus),
        }
        inicio = idx if idx is not None else 0
        horaria = []
        for i in range(inicio, min(inicio + 24, len(horas))):
            cod_h = _wmo_seguro(wmos_h, i)
            horaria.append({
                'hora': horas[i],
                'temperatura': _num(temps_h[i]) if i < len(temps_h) else None,
                'codigo_wmo': cod_h,
                'descricao_pt': descrever_wmo(cod_h)[0],
                'emoji': descrever_wmo(cod_h)[1],
                'prob_precipitacao': _num(probs[i]) if i < len(probs) else None,
            })
        diaria = []
        dias = diaria_api.get('time') or []
        wmos_d = _campo_compat(diaria_api, 'weather_code', 'weathercode') or []
        maxs = diaria_api.get('temperature_2m_max') or []
        mins = diaria_api.get('temperature_2m_min') or []
        probs_d = diaria_api.get('precipitation_probability_max') or []
        for i in range(min(7, len(dias))):
            cod_d = _wmo_seguro(wmos_d, i)
            diaria.append({
                'data': dias[i],
                'codigo_wmo': cod_d,
                'descricao_pt': descrever_wmo(cod_d)[0],
                'emoji': descrever_wmo(cod_d)[1],
                'temp_max': _num(maxs[i]) if i < len(maxs) else None,
                'temp_min': _num(mins[i]) if i < len(mins) else None,
                'prob_precipitacao': _num(probs_d[i]) if i < len(probs_d) else None,
            })
        return {
            'atual': atual,
            'horaria': horaria,
            'diaria': diaria,
            'timezone': dados.get('timezone') or TIMEZONE_PREDEFINIDO,
            'atualizada_em': datetime.utcnow().strftime('%Y-%m-%dT%H:%M'),
            'fonte': 'Open-Meteo',
        }
    except Exception:
        return None


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
