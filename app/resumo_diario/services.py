"""Recolha de dados e composição determinística do Resumo Diário."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from app import db
from app.auth.models import User
from app.calendario.models import Evento
from app.combustiveis import services as combustiveis_services
from app.combustiveis.models import (
    EstadoAtualizacaoCombustiveis,
    UtilizadorCombustivel,
    UtilizadorConcelho,
)
from app.meteorologia import services as meteorologia_services
from app.meteorologia.models import LocalizacaoMeteorologia
from app.resumo_diario.models import ConfiguracaoResumoDiario
from app.tarefas.models import Tarefa


FUSO_HORARIO = ZoneInfo('Europe/Lisbon')
# Coordenadas de Braga, usadas apenas quando o utilizador ainda não escolheu
# uma localização no módulo Meteorologia.
BRAGA_LATITUDE = 41.545448
BRAGA_LONGITUDE = -8.426507
LIMITE_CARACTERES = 900
OPCOES_POR_OMISSAO = {
    'meteorologia': True,
    'tarefas': True,
    'eventos': True,
    'combustiveis': True,
    'fim_de_semana': True,
}


def obter_data_local():
    """Devolve a data actual no fuso horário de Portugal continental."""
    return datetime.now(FUSO_HORARIO).date()


def ler_configuracao_resumo_diario(user_id):
    """Lê as opções sem criar uma linha quando o utilizador ainda não guardou.

    A ausência de configuração equivale aos valores por omissão, incluindo para
    futuras tarefas agendadas que nunca tenham aberto a página de definições.
    """
    configuracao = ConfiguracaoResumoDiario.query.filter_by(user_id=user_id).first()
    if configuracao is None:
        return dict(OPCOES_POR_OMISSAO)
    return {nome: bool(getattr(configuracao, nome)) for nome in OPCOES_POR_OMISSAO}


def obter_ou_criar_configuracao(user_id):
    """Obtém ou cria as preferências, recuperando uma criação concorrente."""
    configuracao = ConfiguracaoResumoDiario.query.filter_by(user_id=user_id).first()
    if configuracao is not None:
        return configuracao

    configuracao = ConfiguracaoResumoDiario(user_id=user_id)
    try:
        # A restrição única é a autoridade final se dois pedidos criarem ao
        # mesmo tempo; o savepoint permite recuperar sem abortar a transacção.
        with db.session.begin_nested():
            db.session.add(configuracao)
            db.session.flush()
        return configuracao
    except IntegrityError:
        return ConfiguracaoResumoDiario.query.filter_by(user_id=user_id).one()


def _meteorologia_por_data(user_id, datas):
    local = LocalizacaoMeteorologia.query.filter_by(user_id=user_id).first()
    latitude = local.latitude if local else BRAGA_LATITUDE
    longitude = local.longitude if local else BRAGA_LONGITUDE
    try:
        previsao = meteorologia_services.obter_previsao(latitude, longitude)
    except Exception:
        return {}
    if not isinstance(previsao, dict):
        return {}

    diaria = previsao.get('diaria') or []
    por_data = {item.get('data'): item for item in diaria if isinstance(item, dict)}
    resultado = {}
    for dia in datas:
        item = por_data.get(dia.isoformat())
        if not item:
            continue
        resultado[dia.isoformat()] = {
            'data': dia.isoformat(),
            'temp_min': item.get('temp_min'),
            'temp_max': item.get('temp_max'),
            'probabilidade_precipitacao': item.get('prob_precipitacao'),
            'descricao': item.get('descricao_pt'),
        }
    return resultado


def _eventos_do_dia(user_id, dia):
    inicio = datetime.combine(dia, time.min)
    fim = inicio + timedelta(days=1)
    eventos = Evento.query.filter(
        Evento.user_id == user_id,
        Evento.data_inicio < fim,
        Evento.data_fim > inicio,
    ).order_by(Evento.data_inicio.asc()).all()
    return [{
        'titulo': evento.titulo,
        'data_inicio': evento.data_inicio.isoformat(),
        'data_fim': evento.data_fim.isoformat(),
        'dia_inteiro': bool(evento.dia_inteiro),
    } for evento in eventos]


def _tarefas_do_dia(user_id, dia):
    hoje = Tarefa.query.filter(
        Tarefa.user_id == user_id,
        Tarefa.concluida.is_(False),
        Tarefa.data_limite == dia,
    ).order_by(Tarefa.data_limite.asc(), Tarefa.id.asc()).all()
    atrasadas = Tarefa.query.filter(
        Tarefa.user_id == user_id,
        Tarefa.concluida.is_(False),
        Tarefa.data_limite.isnot(None),
        Tarefa.data_limite < dia,
    ).order_by(Tarefa.data_limite.asc(), Tarefa.id.asc()).all()

    def serializar(tarefa):
        return {
            'titulo': tarefa.texto,
            'prioridade': tarefa.prioridade,
            'prazo': tarefa.data_limite.isoformat(),
        }

    return ([serializar(tarefa) for tarefa in hoje],
            [serializar(tarefa) for tarefa in atrasadas])


def _combustiveis_do_utilizador(user_id):
    concelhos = [linha.concelho for linha in
                 UtilizadorConcelho.query.filter_by(user_id=user_id).all()]
    tipos = [linha.tipo_combustivel for linha in
             UtilizadorCombustivel.query.filter_by(user_id=user_id).all()]
    if not concelhos or not tipos:
        return None

    resultados = combustiveis_services.obter_precos_para_concelhos(
        concelhos, tipos_utilizador=tipos)
    mais_barato = {}
    for posto, preco in resultados:
        atual = mais_barato.get(preco.tipo_combustivel)
        if atual is None or preco.preco < atual['preco']:
            mais_barato[preco.tipo_combustivel] = {
                'tipo_combustivel': preco.tipo_combustivel,
                'preco': round(preco.preco, 3),
                'posto': posto.nome,
                'concelho': posto.concelho,
            }

    estado = EstadoAtualizacaoCombustiveis.query.filter_by(id=1).first()
    recolha = None
    if estado:
        recolha = {
            'ultima_atualizacao': (estado.ultima_atualizacao.isoformat(sep=' ', timespec='minutes')
                                  if estado.ultima_atualizacao else None),
            'sucesso': estado.ultima_execucao_sucesso,
            'erro': estado.mensagem_erro,
        }
    if not mais_barato and recolha is None:
        return None
    return {
        'mais_barato_por_tipo': [mais_barato[tipo] for tipo in sorted(mais_barato)],
        'recolha': recolha,
    }


def _formatar_hora(iso):
    try:
        return datetime.fromisoformat(iso).strftime('%H:%M')
    except (TypeError, ValueError):
        return ''


def _linha_meteorologia(meteo):
    partes = []
    if meteo.get('temp_min') is not None and meteo.get('temp_max') is not None:
        partes.append(f"{meteo['temp_min']:.0f}–{meteo['temp_max']:.0f} °C")
    if meteo.get('probabilidade_precipitacao') is not None:
        partes.append(f"precipitação {meteo['probabilidade_precipitacao']:.0f}%")
    if meteo.get('descricao'):
        partes.append(str(meteo['descricao']))
    return ', '.join(partes)


def _renderizar_eventos(titulo, eventos):
    if not eventos:
        return None
    linhas = [titulo]
    for evento in eventos:
        hora = _formatar_hora(evento['data_inicio'])
        prefixo = f'{hora} — ' if hora and not evento['dia_inteiro'] else ''
        linhas.append(f"{prefixo}{evento['titulo']}")
    return '\n'.join(linhas)


def _renderizar_tarefas(tarefas, atrasadas):
    if not tarefas and not atrasadas:
        return None
    linhas = ['Tarefas']
    linhas.extend(f"Hoje: {t['titulo']}" for t in tarefas)
    linhas.extend(f"Em atraso ({t['prazo']}): {t['titulo']}" for t in atrasadas)
    return '\n'.join(linhas)


def _renderizar_combustiveis(dados):
    if not dados:
        return None
    linhas = ['Combustíveis']
    for item in dados['mais_barato_por_tipo']:
        linhas.append(
            f"{item['tipo_combustivel']}: {item['preco']:.3f} €/L — "
            f"{item['posto']} ({item['concelho']})"
        )
    recolha = dados.get('recolha')
    if recolha:
        data_recolha = recolha.get('ultima_atualizacao') or 'data desconhecida'
        linhas.append(f"Última recolha: {data_recolha}")
        if recolha.get('sucesso') is False:
            linhas.append(f"Erro na recolha: {recolha.get('erro') or 'sem detalhe'}")
    return '\n'.join(linhas)


def _texto_limitado(blocos):
    """Remove blocos inteiros por ordem inversa da prioridade recebida."""
    activos = list(blocos)
    texto = '\n\n'.join(blocos[chave] for chave in activos)
    while len(texto) > LIMITE_CARACTERES and activos:
        activos.pop()
        texto = '\n\n'.join(blocos[chave] for chave in activos)
    return texto


def gerar_resumo_diario(user_id, data, opcoes=None):
    """Produz secções de resumo e texto curto para o utilizador e a data."""
    if isinstance(data, datetime):
        data = data.date()
    elif isinstance(data, str):
        data = date.fromisoformat(data)
    if not isinstance(data, date):
        raise TypeError('A data tem de ser datetime.date ou uma data ISO.')
    if User.query.filter_by(id=user_id).first() is None:
        raise ValueError('Utilizador inexistente.')

    if opcoes is None:
        opcoes = ler_configuracao_resumo_diario(user_id)
    else:
        opcoes = {nome: bool(opcoes.get(nome, True))
                  for nome in OPCOES_POR_OMISSAO}

    amanha = data + timedelta(days=1)
    secoes = {}
    datas_meteo = [data, amanha]
    sabado = domingo = None
    if data.weekday() == 4:
        sabado = data + timedelta(days=1)
        domingo = data + timedelta(days=2)
        datas_meteo.extend([sabado, domingo])
    meteorologia = (_meteorologia_por_data(user_id, datas_meteo)
                    if opcoes['meteorologia'] else {})

    if data.isoformat() in meteorologia:
        secoes['meteorologia'] = meteorologia[data.isoformat()]
    eventos_hoje = _eventos_do_dia(user_id, data) if opcoes['eventos'] else []
    if eventos_hoje:
        secoes['eventos_hoje'] = eventos_hoje
    tarefas_hoje, tarefas_atrasadas = (
        _tarefas_do_dia(user_id, data) if opcoes['tarefas'] else ([], []))
    if tarefas_hoje:
        secoes['tarefas_hoje'] = tarefas_hoje
    if tarefas_atrasadas:
        secoes['tarefas_atrasadas'] = tarefas_atrasadas
    # À sexta-feira, sábado já é apresentado dentro da secção de fim-de-semana.
    if opcoes['eventos'] and data.weekday() != 4:
        eventos_amanha = _eventos_do_dia(user_id, amanha)
        if eventos_amanha:
            secoes['eventos_amanha'] = eventos_amanha

    if opcoes['combustiveis'] and data.weekday() == 1:
        combustiveis = _combustiveis_do_utilizador(user_id)
        if combustiveis:
            secoes['combustiveis'] = combustiveis

    if opcoes['fim_de_semana'] and data.weekday() == 4:
        dias_fim_de_semana = {}
        for nome, dia in (('sabado', sabado), ('domingo', domingo)):
            dados_dia = {}
            if dia.isoformat() in meteorologia:
                dados_dia['meteorologia'] = meteorologia[dia.isoformat()]
            eventos = _eventos_do_dia(user_id, dia) if opcoes['eventos'] else []
            if eventos:
                dados_dia['eventos'] = eventos
            if dados_dia:
                dias_fim_de_semana[nome] = dados_dia
        if dias_fim_de_semana:
            secoes['fim_de_semana'] = dias_fim_de_semana

    blocos = {}
    if 'meteorologia' in secoes:
        blocos['meteorologia'] = (
            f"Meteorologia: {_linha_meteorologia(secoes['meteorologia'])}")
    if 'eventos_hoje' in secoes:
        blocos['eventos_hoje'] = _renderizar_eventos('Hoje', secoes['eventos_hoje'])
    if 'tarefas_hoje' in secoes or 'tarefas_atrasadas' in secoes:
        blocos['tarefas'] = _renderizar_tarefas(
            secoes.get('tarefas_hoje', []), secoes.get('tarefas_atrasadas', []))
    if 'eventos_amanha' in secoes:
        blocos['eventos_amanha'] = _renderizar_eventos(
            'Amanhã', secoes['eventos_amanha'])
    if 'combustiveis' in secoes:
        blocos['combustiveis'] = _renderizar_combustiveis(secoes['combustiveis'])
    if 'fim_de_semana' in secoes:
        linhas = []
        for nome, titulo in (('sabado', 'Sábado'), ('domingo', 'Domingo')):
            dados_dia = secoes['fim_de_semana'].get(nome)
            if not dados_dia:
                continue
            linhas.append(titulo)
            if 'meteorologia' in dados_dia:
                linhas.append(_linha_meteorologia(dados_dia['meteorologia']))
            linhas.extend(evento['titulo'] for evento in dados_dia.get('eventos', []))
        blocos['fim_de_semana'] = '\n'.join(linhas)

    # A ordem dos blocos define prioridade e também a ordem de apresentação.
    texto = _texto_limitado(blocos)
    return {'data': data.isoformat(), 'secoes': secoes, 'texto': texto}
