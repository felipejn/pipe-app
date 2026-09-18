"""Serviços do módulo Combustíveis — recolha e consulta de preços.

Fonte de dados: **API Aberta** (api.apiaberta.pt) — API com documentação
Swagger pública em https://api.apiaberta.pt/docs. Substitui os endpoints
diretos da DGEG (precoscombustiveis.dgeg.gov.pt), que não podiam ser
adicionados à whitelist do PythonAnywhere por não terem documentação
pública formal.

Cada página é pedida por combustível (`fuel=<slug>`) e o filtro pelos
concelhos de interesse é feito do lado do cliente, sobre o campo
`municipality`. A atualização é chamada de dois sítios:

- tarefa agendada (só automaticamente às terças-feiras);
- botão manual "Atualizar Dados" (força em qualquer dia).

Regra: NÃO usar subprocess nem chamar scripts externos — tudo é função
Python direta dentro do processo Flask/pipe_tasks.
"""

import os
import time
import requests
from datetime import datetime, date as date_cls, timedelta
from app import db
from app.combustiveis.models import Posto, PrecoHistorico, EstadoAtualizacaoCombustiveis

BASE_URL = "https://api.apiaberta.pt/v1/fuel/stations"
API_KEY = os.environ.get('APIABERTA_API_KEY')  # opcional; sem chave = 30 req/min

# Combustíveis acompanhados (fuel_slug -> não precisamos do fuel_name aqui,
# vem sempre na própria resposta da API)
FUEL_SLUGS = ["diesel", "diesel_plus", "gasoline_95"]

MUNICIPIOS_INTERESSE = {"Braga", "Vila Verde", "Amares"}

PAGE_LIMIT = 100
# 300 pedidos/minuto com chave (~0,2 s por pedido); 30/minuto sem chave.
# Com o filtro `district` a paginação completa são ~12 pedidos (≈3-4 páginas
# por combustível), logo ~3 s com chave. Sem chave, ~12 pedidos ainda cabem
# no tier anónimo de 30/min.
PAUSA_ENTRE_PEDIDOS = 0.21  # segundos, margem de segurança face ao rate limit
TENTATIVAS_MAX = 3          # tentativas por página antes de desistir do combustível
PAGINAS_MAX = 60            # corte de segurança contra loop infinito de paginação
LIMIAR_CICLOS_AUSENTE = 2   # nº de recolhas em falta até arquivar
# Distrito cujo nome é prefixo de todos os concelhos de interesse. A API
# filtra por distrito (match por prefixo → inclui "Bragança", daí o filtro por
# concelho é sempre aplicado de cliente para cliente em _paginar_fuel).
DISTRITO_INTERESSE = 'Braga'

# Nomes exactos de postos devolvidos pela API Aberta que devem ser ignorados
# por completo. São entradas antigas da DGEG cujo `id` foi reatribuído e que
# continuam a ser devolvidas com preços congelados — a API não as actualiza —
# criando duplicados no dashboard e falseando o "mais barato por combustível"
# (ex.: "E.S. FERREIROS" a 1,919 € de gasóleo desde Jul/2026, quando o mesmo
# posto, já com o id novo, marca 2,239 €). Excluídos na origem: não são
# criados, actualizados nem reactivados. Ver scripts/remover_postos_ignorados.py.
NOMES_IGNORADOS = {
    'E.S. FERREIROS',
    'E.S. BRAGA PISCINAS I',
    'E.S. BRAGA PISCINAS II',
    'BP Braga João 21',
    'DJB COMBUSTIVEIS',
}

# Comparação sem depender de caixa nem de espaços nas pontas devolvidos pela API.
_NOMES_IGNORADOS_NORMALIZADOS = {nome.strip().casefold() for nome in NOMES_IGNORADOS}


def _nome_ignorado(nome):
    """True se o nome devolvido pela API estiver em NOMES_IGNORADOS."""
    if not nome:
        return False
    return nome.strip().casefold() in _NOMES_IGNORADOS_NORMALIZADOS


# Preços DGEG com mais de este nº de dias são considerados obsoletos: a API
# ainda devolve o posto, mas a DGEG deixou de actualizá-lo — sinal típico de
# posto encerrado ou com id reatribuído — e o valor ficado falseia o "mais
# barato". São excluídos no ambiente de leitura (obter_precos_para_concelhos,
# obter_tipos_combustivel_disponiveis e a contagem total_postos do dashboard),
# porque estes postos continuam a vir em todas as recolhas (ciclos_ausente=0),
# pelo que o arquivamento por ausência nunca os apanha. Station-level.
MAX_DIAS_PRECO_ATIVO = 30


def obter_ids_postos_obsoletos():
    """Ids de postos a excluir dos resultados/dashboard.

    Um posto é obsoleto se:
    - o seu nome está em NOMES_IGNORADOS (duplicado com dados congelados que a
      API continua a devolver), ou
    - não tem nenhum preço registado, ou
    - a sua data de actualização DGEG mais recente (data_atualizacao_dgeg) tem
      mais de MAX_DIAS_PRECO_ATIVO dias.

    A comparação usa o prefixo ISO `YYYY-MM-DD` da string (lexicográfica =
    cronológica). Reverte-se a qualquer momento ajustando MAX_DIAS_PRECO_ATIVO
    ou a lista NOMES_IGNORADOS.
    """
    from sqlalchemy import func
    corte = (datetime.utcnow() - timedelta(days=MAX_DIAS_PRECO_ATIVO)).strftime('%Y-%m-%d')
    ultima_por_posto = (
        db.session.query(
            PrecoHistorico.posto_id,
            func.max(PrecoHistorico.data_atualizacao_dgeg).label('ult_dgeg')
        )
        .group_by(PrecoHistorico.posto_id)
        .subquery()
    )
    linhas = (
        db.session.query(Posto.id)
        .outerjoin(ultima_por_posto, ultima_por_posto.c.posto_id == Posto.id)
        .filter(
            db.or_(
                Posto.nome.in_(list(NOMES_IGNORADOS)),
                ultima_por_posto.c.ult_dgeg.is_(None),
                func.substr(ultima_por_posto.c.ult_dgeg, 1, 10) <= corte,
            )
        )
        .all()
    )
    return [posto_id for (posto_id,) in linhas]


def _headers():
    headers = {'User-Agent': 'PIPE-combustiveis/1.0 (uso pessoal)'}
    if API_KEY:
        # Confirmado ao vivo: com 'X-API-Key' o x-ratelimit-limit sobe de 30
        # para 300. (O header 'Authorization: Bearer' era ignorado pela API.)
        headers['X-API-Key'] = API_KEY
    return headers


def _obter_estado():
    estado = EstadoAtualizacaoCombustiveis.query.get(1)
    if not estado:
        estado = EstadoAtualizacaoCombustiveis(id=1)
        db.session.add(estado)
        db.session.commit()
    return estado


def _get_com_retry(session, params):
    """GET com retry em 429/5xx — um único 429 não deve descartar ~32 páginas.

    Em 429 respeita o 'Retry-After' devolvido pela API; nas restantes
    tentativas usa backoff exponencial.
    """
    for tentativa in range(1, TENTATIVAS_MAX + 1):
        resp = session.get(BASE_URL, params=params, headers=_headers(), timeout=20)
        if resp.status_code == 429 or resp.status_code >= 500:
            if tentativa == TENTATIVAS_MAX:
                resp.raise_for_status()
                return resp
            espera = PAUSA_ENTRE_PEDIDOS
            try:
                espera = max(espera, float(resp.headers.get('Retry-After', 0)))
            except (TypeError, ValueError):
                pass
            time.sleep(espera * tentativa)
            continue
        resp.raise_for_status()
        return resp
    return resp


def _paginar_fuel(session, fuel_slug):
    """Percorre todas as páginas de um combustível e devolve só os
    registos cujo municipality está em MUNICIPIOS_INTERESSE.

    A API filtra por ``district`` no pedido, o que reduz de ~32 para ~4
    páginas por combustível (~12 pedidos ao todo vs ~96 sem filtro). O match
    de distrito é por prefixo, devolvendo também Bragança — inofensivo, porque
    o filtro por concelho é aplicado aqui, de cliente para o cliente.
    """
    encontrados = []
    page = 1
    while True:
        params = {'fuel': fuel_slug, 'district': DISTRITO_INTERESSE,
                  'page': page, 'limit': PAGE_LIMIT}
        resp = _get_com_retry(session, params)
        corpo = resp.json()

        for registo in corpo.get('data', []):
            if registo.get('municipality') in MUNICIPIOS_INTERESSE:
                encontrados.append(registo)

        meta = corpo.get('meta', {})
        paginas = meta.get('pages', 1)
        if page >= paginas or page >= PAGINAS_MAX:
            break
        page += 1
        time.sleep(PAUSA_ENTRE_PEDIDOS)

    return encontrados


def atualizar_precos_se_necessario(forcar=False, hoje=None):
    """
    Retorna dict com as chaves 'executado', 'sucesso',
    'postos_verificados', 'postos_atualizados' (nº de postos
    verificados), 'precos_novos', 'postos_na_bd', 'postos_arquivados'
    (nº de postos que passaram a ativo=False nesta chamada) e 'erro'.

    Fonte de dados: API Aberta (api.apiaberta.pt/v1/fuel/stations), autenticada
    via header X-API-Key (chave em APIABERTA_API_KEY). Sem chave, tier anónimo
    de 30 pedidos/min; com chave, 300/min. Rate limit respeitado com
    PAUSA_ENTRE_PEDIDOS (~0,21s) e retry em 429 respeitando Retry-After.

    Os postos cujo nome conste de NOMES_IGNORADOS são descartados antes de
    qualquer escrita (ver a constante, no topo do módulo).
    """
    hoje = hoje or date_cls.today()

    if not forcar and hoje.weekday() != 1:  # 1 = terça-feira
        return {'executado': False, 'sucesso': True, 'postos_atualizados': 0,
                'postos_arquivados': 0, 'erro': None}

    estado = _obter_estado()

    # Evita correr duas vezes na mesma terça-feira, caso a tarefa seja
    # disparada mais do que uma vez no mesmo dia
    if not forcar and estado.ultima_atualizacao and estado.ultima_atualizacao.date() == hoje:
        return {'executado': False, 'sucesso': True, 'postos_atualizados': 0,
                'postos_arquivados': 0, 'erro': None}

    session = requests.Session()
    erros = []
    postos_vistos = set()
    precos_gravados = 0
    postos_arquivados = 0

    for fuel_slug in FUEL_SLUGS:
        try:
            registos = _paginar_fuel(session, fuel_slug)
        except requests.RequestException as exc:
            erros.append(f'Falhou fuel={fuel_slug}: {exc}')
            continue

        for r in registos:
            # Postos em NOMES_IGNORADOS são descartados na origem: não criam
            # nem actualizam Posto, não gravam histórico e não contam como
            # vistos (logo, se ainda existirem na BD, o arquivamento
            # automático trata deles).
            if _nome_ignorado(r.get('name')):
                continue

            posto_id = r['station_id']
            posto = Posto.query.get(posto_id) or Posto(id=posto_id)
            posto.nome = r.get('name')
            posto.marca = r.get('brand')
            posto.morada = r.get('address')
            posto.localidade = r.get('locality')
            posto.cod_postal = r.get('postal_code')
            posto.concelho = r.get('municipality')
            db.session.add(posto)
            db.session.flush()

            # Posto presente nesta recolha: fica (ou volta a ficar) activo e o
            # contador de ausências é reiniciado. Cobre tanto o caso normal
            # como a reactivação automática de um posto que tinha sido
            # arquivado e voltou a aparecer na API. Tem de vir antes do bloco
            # de deduplicação, para também correr no ramo do `continue`.
            posto.ativo = True
            posto.ciclos_ausente = 0

            # Deduplicação: só grava histórico quando há alteração real. A API
            # devolve updated_at (timestamp DGEG) + preço; se coincidirem com o
            # último registo conhecido do mesmo posto+combustível, nada grava.
            ultimo = (PrecoHistorico.query
                      .filter_by(posto_id=posto.id, tipo_combustivel=r.get('fuel_name'))
                      .order_by(PrecoHistorico.data_recolha.desc()).first())
            if (ultimo is not None
                    and ultimo.preco == r.get('price_eur')
                    and ultimo.data_atualizacao_dgeg == r.get('updated_at')):
                postos_vistos.add(posto_id)
                continue

            db.session.add(PrecoHistorico(
                posto_id=posto.id,
                tipo_combustivel=r.get('fuel_name'),
                preco=r.get('price_eur'),
                data_atualizacao_dgeg=r.get('updated_at'),
            ))
            precos_gravados += 1
            postos_vistos.add(posto_id)

    sucesso = len(erros) == 0

    # Arquivamento automático: um posto activo que não veio nesta recolha
    # acumula uma ausência; ao atingir LIMIAR_CICLOS_AUSENTE é marcado como
    # inactivo — deixa de aparecer no dashboard e nos cálculos de "mais
    # barato", mas todo o histórico associado é preservado. Só corre quando a
    # recolha não teve erros: em caso de falha parcial (ex.: um combustível
    # sem resposta) todos os postos desse combustível ficariam fora de
    # `postos_vistos` e seriam contados como ausentes por engano.
    if sucesso:
        ids_vistos = postos_vistos
        postos_ausentes = Posto.query.filter(
            Posto.ativo.is_(True),
            ~Posto.id.in_(ids_vistos)
        ).all()
        for posto in postos_ausentes:
            posto.ciclos_ausente += 1
            if posto.ciclos_ausente >= LIMIAR_CICLOS_AUSENTE:
                posto.ativo = False
                postos_arquivados += 1

    # Marca "correu hoje" só quando tudo correu bem: em caso de falha permite
    # retry na mesma terça-feira, em vez de perder o dia inteiro.
    if sucesso:
        estado.ultima_atualizacao = datetime.utcnow()
    estado.ultima_execucao_sucesso = sucesso
    estado.mensagem_erro = '; '.join(erros) if erros else None
    db.session.commit()

    return {
        'executado': True,
        'sucesso': sucesso,
        'postos_verificados': len(postos_vistos),
        'postos_atualizados': len(postos_vistos),  # compat. retroativa
        'precos_novos': precos_gravados,
        'postos_arquivados': postos_arquivados,
        'postos_na_bd': Posto.query.count(),
        'erro': estado.mensagem_erro,
    }

def obter_tipos_combustivel_disponiveis(concelhos, tipos_utilizador=None):
    query = (
        db.session.query(PrecoHistorico.tipo_combustivel)
        .join(Posto, Posto.id == PrecoHistorico.posto_id)
        .filter(Posto.concelho.in_(concelhos))
        .filter(~Posto.id.in_(obter_ids_postos_obsoletos()))
    )
    if tipos_utilizador:
        query = query.filter(PrecoHistorico.tipo_combustivel.in_(tipos_utilizador))
    return [t[0] for t in query.distinct().order_by(PrecoHistorico.tipo_combustivel).all()]

def obter_precos_para_concelhos(concelhos, tipos_utilizador=None, tipo_selecionado=None):
    """Últimos preços por posto+combustível, filtrados por concelhos (e, se existir, universo de tipos)."""
    from sqlalchemy import func
    subq = (
        db.session.query(
            PrecoHistorico.posto_id,
            PrecoHistorico.tipo_combustivel,
            func.max(PrecoHistorico.data_recolha).label('max_data')
        )
        .group_by(PrecoHistorico.posto_id, PrecoHistorico.tipo_combustivel)
        .subquery()
    )
    query = (
        db.session.query(Posto, PrecoHistorico)
        .join(PrecoHistorico, PrecoHistorico.posto_id == Posto.id)
        .join(subq, db.and_(
            PrecoHistorico.posto_id == subq.c.posto_id,
            PrecoHistorico.tipo_combustivel == subq.c.tipo_combustivel,
            PrecoHistorico.data_recolha == subq.c.max_data,
        ))
        .filter(Posto.concelho.in_(concelhos))
        .filter(Posto.ativo.is_(True))
        .filter(~Posto.id.in_(obter_ids_postos_obsoletos()))
    )
    if tipos_utilizador:
        query = query.filter(PrecoHistorico.tipo_combustivel.in_(tipos_utilizador))
    if tipo_selecionado and tipo_selecionado != 'Todos':
        query = query.filter(PrecoHistorico.tipo_combustivel == tipo_selecionado)
    return query.order_by(Posto.concelho, PrecoHistorico.tipo_combustivel, PrecoHistorico.preco).all()