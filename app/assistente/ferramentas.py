"""Ferramentas de tool use — funções que o modelo de IA pode invocar.

Cada função recebe user_id e filtra TODAS as queries por esse valor
ao nível de Python/SQLAlchemy. Este filtro é inegociável.
"""

import time
from datetime import date, datetime, timedelta

from flask import session

from app.tarefas.models import Lista, Tarefa, TagTarefa
from app.notas.models import ItemChecklist, Nota, EtiquetaNota
from app.euromilhoes.models import Jogo
from app.calendario.models import Evento
from app.cambio.service import MOEDAS as MOEDAS_CAMBIO, obter_taxa as obter_taxa_cambio
from app.passwords.generator import gerar_password, gerar_passphrase, gerar_pin
from app import db


# ── Constantes de controlo (antes de DEFINICOES_FERRAMENTAS) ─────────────────

# Cores válidas do módulo Calendário
CORES_EVENTO = (
    'tomate', 'flamingo', 'tangerina', 'banana', 'salvia',
    'basil', 'peacock', 'mirtilo', 'lavanda', 'uva', 'grafite',
)

# Ferramentas que alteram dados — sujeitas a limite de débito e só
# disponíveis quando a sessão está em modo 'escrita'.
FERRAMENTAS_ESCRITA = {
    'criar_tarefa', 'alternar_tarefa', 'apagar_tarefa',
    'criar_nota', 'alternar_nota_acao', 'apagar_nota',
    'criar_evento', 'atualizar_evento', 'apagar_evento',
    'gerar_credencial',
}

LIMITE_ESCRITAS_POR_MINUTO = 10


def _limite_escrita_excedido():
    """Limite de débito simples para ferramentas de escrita, por sessão."""
    agora = time.time()
    janela = [t for t in session.get('assistente_escritas_ts', []) if agora - t < 60]
    if len(janela) >= LIMITE_ESCRITAS_POR_MINUTO:
        session['assistente_escritas_ts'] = janela
        return True
    janela.append(agora)
    session['assistente_escritas_ts'] = janela
    session.modified = True
    return False


def _obter_ou_criar_lista(user_id, nome_lista=None):
    """Devolve a lista pelo nome (case-insensitive) ou cria 'Geral' se não houver nenhuma."""
    if nome_lista:
        lista = Lista.query.filter_by(user_id=user_id).filter(
            Lista.nome.ilike(nome_lista)
        ).first()
        if lista:
            return lista
        lista = Lista(nome=nome_lista, user_id=user_id)
        db.session.add(lista)
        db.session.flush()
        return lista

    lista = Lista.query.filter_by(user_id=user_id).order_by(Lista.ordem.asc()).first()
    if lista:
        return lista
    lista = Lista(nome='Geral', icone='📋', user_id=user_id)
    db.session.add(lista)
    db.session.flush()
    return lista


def _obter_ou_criar_tags(user_id, tags_texto):
    """tags_texto: string separada por vírgulas. Devolve lista de TagTarefa."""
    if not tags_texto:
        return []
    nomes = [t.strip().lower() for t in tags_texto.split(',') if t.strip()]
    resultado = []
    for nome in nomes:
        tag = TagTarefa.query.filter_by(user_id=user_id, nome=nome).first()
        if not tag:
            tag = TagTarefa(nome=nome, user_id=user_id)
            db.session.add(tag)
            db.session.flush()
        resultado.append(tag)
    return resultado


def _obter_ou_criar_etiquetas_nota(user_id, etiquetas):
    """etiquetas: lista de strings. Devolve lista de EtiquetaNota."""
    if not etiquetas:
        return []
    resultado = []
    for nome in etiquetas:
        nome = nome.strip().lower()
        if not nome:
            continue
        etq = EtiquetaNota.query.filter_by(user_id=user_id, nome=nome).first()
        if not etq:
            etq = EtiquetaNota(nome=nome, user_id=user_id)
            db.session.add(etq)
            db.session.flush()
        resultado.append(etq)
    return resultado


# ── Definições de ferramentas (formato OpenAI Function Calling) ──────────────────

DEFINICOES_FERRAMENTAS_LEITURA = [
    {
        'type': 'function',
        'function': {
            'name': 'get_tarefas',
            'description': 'Consulta as tarefas do utilizador. Permite filtrar por lista, estado e se estão em atraso.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'lista': {
                        'type': 'string',
                        'description': 'Nome ou ID da lista para filtrar (opcional).',
                    },
                    'estado': {
                        'type': 'string',
                        'enum': ['pendentes', 'concluidas', 'todas'],
                        'description': 'Estado das tarefas a devolver.',
                    },
                    'atrasadas': {
                        'type': 'boolean',
                        'description': 'Se True, devolve apenas tarefas em atraso (pendentes com prazo ultrapassado).',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_notas',
            'description': 'Consulta as notas do utilizador, como o Google Keep.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'busca': {
                        'type': 'string',
                        'description': 'Termo de pesquisa no título ou conteúdo.',
                    },
                    'etiqueta': {
                        'type': 'string',
                        'description': 'Nome da etiqueta para filtrar.',
                    },
                    'arquivadas': {
                        'type': 'boolean',
                        'description': 'Se True, inclui notas arquivadas.',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_euromilhoes',
            'description': 'Consulta os últimos jogos de Euromilhões do utilizador.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'ultimos_n': {
                        'type': 'integer',
                        'description': 'Número de jogos recentes a devolver (default: 5).',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_resumo_geral',
            'description': 'Devolve um resumo rápido de todos os módulos do PIPE para o utilizador (total de tarefas, notas, jogos, etc.).',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_eventos',
            'description': 'Consulta os eventos do calendário do utilizador.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'data': {
                        'type': 'string',
                        'description': 'Data no formato AAAA-MM-DD para filtrar eventos desse dia (opcional).',
                    },
                    'futuros': {
                        'type': 'boolean',
                        'description': 'Se True, devolve apenas eventos futuros.',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_cambio',
            'description': 'Converte um valor entre moedas com taxas em tempo real (Wise + fallback).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'origem': {
                        'type': 'string',
                        'description': 'Código da moeda de origem (ex: EUR, USD, BRL).',
                    },
                    'destino': {
                        'type': 'string',
                        'description': 'Código da moeda de destino (ex: BRL, EUR, USD).',
                    },
                    'valor': {
                        'type': 'number',
                        'description': 'Valor a converter (deve ser maior que zero).',
                    },
                },
                'required': ['origem', 'destino', 'valor'],
            },
        },
    },
]

DEFINICOES_FERRAMENTAS_ESCRITA_EXTRA = [
    {
        'type': 'function',
        'function': {
            'name': 'criar_tarefa',
            'description': 'Cria uma nova tarefa numa lista do utilizador. Se a lista não existir, é criada automaticamente.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'texto': {'type': 'string', 'description': 'Texto da tarefa.'},
                    'prioridade': {'type': 'string', 'enum': ['baixa', 'media', 'alta']},
                    'data_limite': {'type': 'string', 'description': 'Formato AAAA-MM-DD (opcional).'},
                    'lista_nome': {'type': 'string', 'description': 'Nome da lista (opcional; usa/cria "Geral" se omitido).'},
                    'tags': {'type': 'string', 'description': 'Etiquetas separadas por vírgula (opcional).'},
                },
                'required': ['texto'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'alternar_tarefa',
            'description': 'Marca uma tarefa como concluída ou volta a marcá-la como pendente.',
            'parameters': {
                'type': 'object',
                'properties': {'tarefa_id': {'type': 'integer'}},
                'required': ['tarefa_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'apagar_tarefa',
            'description': 'Apaga uma tarefa. Na primeira chamada (sem confirmado=true) devolve um pedido de confirmação — pergunta ao utilizador e só voltas a chamar com confirmado=true se ele confirmar.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'tarefa_id': {'type': 'integer'},
                    'confirmado': {'type': 'boolean', 'description': 'Só true depois do utilizador confirmar explicitamente.'},
                },
                'required': ['tarefa_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'criar_nota',
            'description': 'Cria uma nota de texto livre ou checklist.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'titulo': {'type': 'string'},
                    'corpo': {'type': 'string', 'description': 'Texto livre (só para tipo=texto).'},
                    'tipo': {'type': 'string', 'enum': ['texto', 'checklist']},
                    'cor': {'type': 'string', 'enum': ['padrao', 'vermelho', 'laranja', 'amarelo', 'verde', 'azul', 'roxo', 'cinzento']},
                    'etiquetas': {'type': 'array', 'items': {'type': 'string'}},
                    'itens': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Itens do checklist (só para tipo=checklist).'},
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'alternar_nota_acao',
            'description': 'Fixa/desfixa, arquiva/desarquiva uma nota, ou marca/desmarca um item de checklist.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'nota_id': {'type': 'integer'},
                    'accao': {'type': 'string', 'enum': ['toggle_fixada', 'toggle_arquivada', 'toggle_item']},
                    'item_id': {'type': 'integer', 'description': 'Obrigatório apenas quando accao=toggle_item.'},
                },
                'required': ['nota_id', 'accao'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'apagar_nota',
            'description': 'Apaga uma nota. Sem confirmado=true devolve pedido de confirmação primeiro.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'nota_id': {'type': 'integer'},
                    'confirmado': {'type': 'boolean'},
                },
                'required': ['nota_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'criar_evento',
            'description': 'Cria um evento no Calendário.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'titulo': {'type': 'string'},
                    'data_inicio': {'type': 'string', 'description': 'ISO 8601, ex: 2026-09-20T14:00:00.'},
                    'data_fim': {'type': 'string', 'description': 'ISO 8601.'},
                    'descricao': {'type': 'string'},
                    'localizacao': {'type': 'string'},
                    'cor': {'type': 'string', 'enum': ['tomate', 'flamingo', 'tangerina', 'banana', 'salvia', 'basil', 'peacock', 'mirtilo', 'lavanda', 'uva', 'grafite']},
                    'dia_inteiro': {'type': 'boolean'},
                    'notificar': {'type': 'boolean'},
                },
                'required': ['titulo', 'data_inicio', 'data_fim'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'atualizar_evento',
            'description': 'Actualiza campos de um evento existente. Só envia os campos que mudam.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'evento_id': {'type': 'integer'},
                    'titulo': {'type': 'string'},
                    'data_inicio': {'type': 'string'},
                    'data_fim': {'type': 'string'},
                    'descricao': {'type': 'string'},
                    'localizacao': {'type': 'string'},
                    'cor': {'type': 'string'},
                    'dia_inteiro': {'type': 'boolean'},
                    'notificar': {'type': 'boolean'},
                },
                'required': ['evento_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'apagar_evento',
            'description': 'Apaga um evento. Sem confirmado=true devolve pedido de confirmação primeiro.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'evento_id': {'type': 'integer'},
                    'confirmado': {'type': 'boolean'},
                },
                'required': ['evento_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'gerar_credencial',
            'description': 'Gera uma password, passphrase ou PIN aleatório. Não guarda nada.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'modo': {'type': 'string', 'enum': ['password', 'passphrase', 'pin']},
                    'comprimento': {'type': 'integer', 'description': 'Para password (8-64) ou pin (4-12).'},
                    'maiusculas': {'type': 'boolean'},
                    'minusculas': {'type': 'boolean'},
                    'numeros': {'type': 'boolean'},
                    'simbolos': {'type': 'boolean'},
                    'excluir_ambiguos': {'type': 'boolean'},
                    'num_palavras': {'type': 'integer', 'description': 'Para passphrase (3-10).'},
                },
            },
        },
    },
]

DEFINICOES_FERRAMENTAS_ESCRITA = DEFINICOES_FERRAMENTAS_LEITURA + DEFINICOES_FERRAMENTAS_ESCRITA_EXTRA

# Mapa nome → função executável
REGISTO_FERRAMENTAS = {
    'get_tarefas': 'get_tarefas',
    'get_notas': 'get_notas',
    'get_euromilhoes': 'get_euromilhoes',
    'get_resumo_geral': 'get_resumo_geral',
    'get_eventos': 'get_eventos',
    'get_cambio': 'get_cambio',
    'criar_tarefa': 'criar_tarefa',
    'alternar_tarefa': 'alternar_tarefa',
    'apagar_tarefa': 'apagar_tarefa',
    'criar_nota': 'criar_nota',
    'alternar_nota_acao': 'alternar_nota_acao',
    'apagar_nota': 'apagar_nota',
    'criar_evento': 'criar_evento',
    'atualizar_evento': 'atualizar_evento',
    'apagar_evento': 'apagar_evento',
    'gerar_credencial': 'gerar_credencial',
}


# ── Implementação com queries reais ─────────────────────────────────────────────


def get_tarefas(user_id, lista=None, estado=None, atrasadas=False):
    """Consulta tarefas do utilizador, com filtros opcionais.

    Args:
        user_id: ID do utilizador (obrigatório).
        lista: nome ou ID da lista para filtrar (opcional).
        estado: 'pendentes', 'concluidas' ou 'todas'.
        atrasadas: se True, só tarefas pendentes com prazo ultrapassado.

    Returns:
        Lista de dicts com id, titulo, prioridade, prazo, concluida, lista_nome.
    """
    q = Tarefa.query.filter_by(user_id=user_id)

    if estado == 'pendentes':
        q = q.filter_by(concluida=False)
    elif estado == 'concluidas':
        q = q.filter_by(concluida=True)

    if atrasadas:
        hoje = date.today()
        q = q.filter(
            Tarefa.concluida == False,  # noqa: E712
            Tarefa.data_limite.isnot(None),
            Tarefa.data_limite < hoje,
        )

    if lista:
        # Se parece um ID numérico, filtra por ID; senão, por nome
        if lista.isdigit():
            q = q.filter_by(lista_id=int(lista))
        else:
            lista_ids = {
                l.id for l in Lista.query.filter_by(
                    user_id=user_id
                ).filter(Lista.nome.ilike(f'%{lista}%')).all()
            }
            if lista_ids:
                q = q.filter(Tarefa.lista_id.in_(lista_ids))
            else:
                return []

    resultados = q.order_by(
        Tarefa.concluida.asc(),
        Tarefa.data_limite.asc().nullslast(),
    ).all()

    return [
        {
            'id': t.id,
            'titulo': t.texto,
            'prioridade': t.prioridade,
            'prazo': t.data_limite.isoformat() if t.data_limite else None,
            'concluida': t.concluida,
            'lista_nome': t.lista.nome if t.lista else 'Sem lista',
        }
        for t in resultados
    ]


def get_notas(user_id, busca=None, etiqueta=None, arquivadas=False):
    """Consulta notas do utilizador, com filtros opcionais.

    Args:
        user_id: ID do utilizador (obrigatório).
        busca: termo de pesquisa no título ou corpo.
        etiqueta: nome da etiqueta para filtrar.
        arquivadas: se False (default), exclui notas arquivadas.

    Returns:
        Lista de dicts com id, titulo, corpo (max 200 chars), etiquetas, fixada.
    """
    q = Nota.query.filter_by(user_id=user_id)

    if not arquivadas:
        q = q.filter_by(arquivada=False)

    if busca:
        q = q.filter(
            Nota.titulo.ilike(f'%{busca}%') | Nota.corpo.ilike(f'%{busca}%')
        )

    if etiqueta:
        q = q.join(Nota.etiquetas).filter(EtiquetaNota.nome == etiqueta)

    resultados = q.order_by(Nota.fixada.desc(), Nota.data_edicao.desc()).all()

    return [
        {
            'id': n.id,
            'titulo': n.titulo or 'Sem título',
            'corpo': (n.corpo[:200] + '…' if n.corpo and len(n.corpo) > 200 else (n.corpo or '')),
            'etiquetas': [e.nome for e in n.etiquetas],
            'fixada': n.fixada,
            'tipo': n.tipo,
        }
        for n in resultados
    ]


def get_euromilhoes(user_id, ultimos_n=5):
    """Consulta os últimos N jogos de Euromilhões do utilizador.

    Args:
        user_id: ID do utilizador (obrigatório).
        ultimos_n: número de jogos recentes a devolver (default: 5).

    Returns:
        Lista de dicts com id, numeros, estrelas, data, resultado.
    """
    resultados = (
        Jogo.query.filter_by(user_id=user_id)
        .order_by(Jogo.data_sorteio.desc())
        .limit(ultimos_n)
        .all()
    )

    return [
        {
            'id': j.id,
            'numeros': j.get_numeros(),
            'estrelas': j.get_estrelas(),
            'data': j.data_sorteio.isoformat(),
            'resultado': None,  # resultado é obtido via API externa, não está na BD
        }
        for j in resultados
    ]


def get_resumo_geral(user_id):
    """Devolve estatísticas rápidas de todos os módulos para o utilizador.

    Args:
        user_id: ID do utilizador (obrigatório).

    Returns:
        Dict com contagens sumarizadas.
    """
    hoje = date.today()

    tarefas_total = Tarefa.query.filter_by(user_id=user_id).count()
    tarefas_em_atraso = Tarefa.query.filter(
        Tarefa.user_id == user_id,
        Tarefa.concluida == False,  # noqa: E712
        Tarefa.data_limite.isnot(None),
        Tarefa.data_limite < hoje,
    ).count()
    tarefas_concluidas_hoje = Tarefa.query.filter(
        Tarefa.user_id == user_id,
        Tarefa.concluida == True,  # noqa: E712
        Tarefa.data_conclusao.isnot(None),
        Tarefa.data_conclusao >= hoje,
    ).count()

    notas_total = Nota.query.filter_by(user_id=user_id, arquivada=False).count()
    notas_fixadas = Nota.query.filter_by(user_id=user_id, fixada=True).count()

    euromilhoes_jogos_total = Jogo.query.filter_by(user_id=user_id).count()

    return {
        'tarefas_total': tarefas_total,
        'tarefas_em_atraso': tarefas_em_atraso,
        'tarefas_concluidas_hoje': tarefas_concluidas_hoje,
        'notas_total': notas_total,
        'notas_fixadas': notas_fixadas,
        'euromilhoes_jogos_total': euromilhoes_jogos_total,
    }


def get_eventos(user_id, data=None, futuros=False):
    """Consulta eventos do calendário do utilizador, com filtros opcionais.

    Args:
        user_id: ID do utilizador (obrigatório).
        data: data no formato AAAA-MM-DD para filtrar eventos desse dia (opcional).
        futuros: se True, só devolve eventos futuros (data_inicio >= agora).

    Returns:
        Lista de dicts com id, titulo, descricao, localizacao, data_inicio,
        data_fim, dia_inteiro, cor, notificar, notificado_em, criado_em.
    """
    q = Evento.query.filter_by(user_id=user_id)

    if data:
        try:
            data_dt = datetime.strptime(data, '%Y-%m-%d')
            q = q.filter(
                Evento.data_inicio >= data_dt,
                Evento.data_inicio < data_dt + timedelta(days=1),
            )
        except ValueError:
            return {'erro': f'Data inválida: "{data}". Usa o formato AAAA-MM-DD.'}

    if futuros:
        agora = datetime.utcnow()
        q = q.filter(Evento.data_inicio >= agora)

    resultados = q.order_by(Evento.data_inicio.asc()).all()

    return [
        {
            'id': e.id,
            'titulo': e.titulo,
            'descricao': e.descricao,
            'localizacao': e.localizacao,
            'data_inicio': e.data_inicio.isoformat() if e.data_inicio else None,
            'data_fim': e.data_fim.isoformat() if e.data_fim else None,
            'dia_inteiro': e.dia_inteiro,
            'cor': e.cor,
            'notificar': e.notificar,
            'notificado_em': e.notificado_em.isoformat() if e.notificado_em else None,
            'criado_em': e.criado_em.isoformat() if e.criado_em else None,
        }
        for e in resultados
    ]


def get_cambio(user_id, origem=None, destino=None, valor=None):
    """Converte um valor entre moedas com taxas em tempo real.

    Ferramenta de leitura (stateless): não consulta a BD nem guarda nada.
    O user_id é aceite por convenção do despachante, mas não é usado.

    Args:
        user_id: ID do utilizador (obrigatório por convenção, ignorado).
        origem: código da moeda de origem (ex: EUR).
        destino: código da moeda de destino (ex: BRL).
        valor: montante a converter (deve ser maior que zero).

    Returns:
        Dict com origem, destino, valor, resultado, taxa, fonte e metadados,
        ou dict com chave 'erro' quando os argumentos são inválidos ou o
        serviço de cotações está indisponível.
    """
    if not origem or not destino or valor is None:
        return {'erro': 'Indica a moeda de origem, a moeda de destino e o valor a converter.'}

    origem = str(origem).strip().upper()
    destino = str(destino).strip().upper()
    if origem not in MOEDAS_CAMBIO:
        return {'erro': f'Moeda de origem inválida: "{origem}". Moedas suportadas: {", ".join(sorted(MOEDAS_CAMBIO))}.'}
    if destino not in MOEDAS_CAMBIO:
        return {'erro': f'Moeda de destino inválida: "{destino}". Moedas suportadas: {", ".join(sorted(MOEDAS_CAMBIO))}.'}

    try:
        montante = float(valor)
    except (TypeError, ValueError):
        return {'erro': f'Valor inválido: "{valor}". Indica um número maior que zero.'}
    if montante <= 0:
        return {'erro': 'O valor a converter deve ser maior que zero.'}

    resultado = obter_taxa_cambio(origem, destino, montante)
    if resultado is None:
        return {'erro': 'Não foi possível obter a cotação de momento. Tenta novamente mais tarde.'}

    return {
        'origem': origem,
        'destino': destino,
        'valor': montante,
        'resultado': resultado['resultado'],
        'taxa': resultado['taxa'],
        'fonte': resultado['fonte'],
        'data': resultado['data'],
        'total_fees': resultado['total_fees'],
        'rate': resultado['rate'],
        'fees': resultado['fees'],
    }


# ── Tarefas — escrita ────────────────────────────────────────────────────

def criar_tarefa(user_id, texto, prioridade='media', data_limite=None, lista_nome=None, tags=None):
    """Cria uma nova tarefa. Se a lista não existir, é criada; se nenhuma for indicada, usa/cria 'Geral'."""
    if prioridade not in Tarefa.PRIORIDADES:
        prioridade = 'media'

    prazo = None
    if data_limite:
        try:
            prazo = datetime.strptime(data_limite, '%Y-%m-%d').date()
        except ValueError:
            return {'erro': f'Data limite inválida: "{data_limite}". Usa o formato AAAA-MM-DD.'}

    lista = _obter_ou_criar_lista(user_id, lista_nome)
    tarefa = Tarefa(
        texto=texto,
        prioridade=prioridade,
        data_limite=prazo,
        lista_id=lista.id,
        user_id=user_id,
    )
    if tags:
        tarefa.tags = _obter_ou_criar_tags(user_id, tags)

    db.session.add(tarefa)
    db.session.commit()
    return {'ok': True, 'id': tarefa.id, 'texto': tarefa.texto, 'lista': lista.nome}


def alternar_tarefa(user_id, tarefa_id):
    """Alterna o estado concluída/pendente de uma tarefa do utilizador."""
    tarefa = Tarefa.query.filter_by(id=tarefa_id, user_id=user_id).first()
    if not tarefa:
        return {'erro': 'Tarefa não encontrada.'}

    tarefa.concluida = not tarefa.concluida
    tarefa.data_conclusao = datetime.utcnow() if tarefa.concluida else None
    if tarefa.concluida:
        tarefa.notificada_em = None
    db.session.commit()
    return {'ok': True, 'id': tarefa.id, 'concluida': tarefa.concluida}


def apagar_tarefa(user_id, tarefa_id, confirmado=False):
    """Apaga uma tarefa. Exige confirmação explícita do utilizador antes de executar."""
    tarefa = Tarefa.query.filter_by(id=tarefa_id, user_id=user_id).first()
    if not tarefa:
        return {'erro': 'Tarefa não encontrada.'}

    if not confirmado:
        return {
            'confirmacao_necessaria': True,
            'mensagem': f'Confirmas que queres apagar a tarefa "{tarefa.texto}"?',
        }

    db.session.delete(tarefa)
    db.session.commit()
    return {'ok': True}


# ── Notas — escrita ──────────────────────────────────────────────────────

def criar_nota(user_id, titulo=None, corpo=None, tipo='texto', cor='padrao', etiquetas=None, itens=None):
    """Cria uma nova nota, de texto livre ou checklist."""
    if tipo not in Nota.TIPOS:
        tipo = Nota.TIPO_TEXTO
    if cor not in Nota.CORES:
        cor = 'padrao'

    nota = Nota(titulo=titulo, corpo=corpo if tipo == Nota.TIPO_TEXTO else None, tipo=tipo, cor=cor, user_id=user_id)
    if etiquetas:
        nota.etiquetas = _obter_ou_criar_etiquetas_nota(user_id, etiquetas)

    db.session.add(nota)
    db.session.flush()

    if tipo == Nota.TIPO_CHECKLIST and itens:
        for i, texto_item in enumerate(itens):
            db.session.add(ItemChecklist(texto=texto_item, nota_id=nota.id, ordem=i))

    db.session.commit()
    return {'ok': True, 'id': nota.id, 'titulo': nota.titulo or 'Sem título'}


def alternar_nota_acao(user_id, nota_id, accao, item_id=None):
    """accao: 'toggle_fixada', 'toggle_arquivada' ou 'toggle_item' (requer item_id).

    Alinhado com app/notas/routes.py → accao(): ao arquivar, desfixa a nota;
    data_edicao é actualizada em todas as acções.
    """
    nota = Nota.query.filter_by(id=nota_id, user_id=user_id).first()
    if not nota:
        return {'erro': 'Nota não encontrada.'}

    if accao == 'toggle_fixada':
        nota.fixada = not nota.fixada
    elif accao == 'toggle_arquivada':
        nota.arquivada = not nota.arquivada
        nota.fixada = False
    elif accao == 'toggle_item':
        if not item_id:
            return {'erro': 'item_id é obrigatório para toggle_item.'}
        item = ItemChecklist.query.filter_by(id=item_id, nota_id=nota.id).first()
        if not item:
            return {'erro': 'Item não encontrado.'}
        item.feito = not item.feito
    else:
        return {'erro': f'Acção desconhecida: {accao}'}

    nota.data_edicao = datetime.utcnow()
    db.session.commit()
    return {'ok': True}


def apagar_nota(user_id, nota_id, confirmado=False):
    """Apaga uma nota. Exige confirmação explícita antes de executar."""
    nota = Nota.query.filter_by(id=nota_id, user_id=user_id).first()
    if not nota:
        return {'erro': 'Nota não encontrada.'}

    if not confirmado:
        return {
            'confirmacao_necessaria': True,
            'mensagem': f'Confirmas que queres apagar a nota {nota.titulo or "sem título"}?',
        }

    db.session.delete(nota)
    db.session.commit()
    return {'ok': True}


# ── Calendário — escrita ─────────────────────────────────────────────────

def criar_evento(user_id, titulo, data_inicio, data_fim, descricao=None, localizacao=None,
                  cor='tomate', dia_inteiro=False, notificar=True):
    try:
        inicio = datetime.fromisoformat(data_inicio)
        fim = datetime.fromisoformat(data_fim)
    except (ValueError, TypeError):
        return {'erro': 'Datas inválidas. Usa o formato ISO (ex: 2026-09-20T14:00:00).'}

    if fim < inicio:
        return {'erro': 'A data de fim não pode ser anterior à data de início.'}
    if cor not in CORES_EVENTO:
        cor = 'tomate'

    evento = Evento(
        user_id=user_id, titulo=titulo, descricao=descricao, localizacao=localizacao,
        data_inicio=inicio, data_fim=fim, dia_inteiro=dia_inteiro, cor=cor, notificar=notificar,
    )
    db.session.add(evento)
    db.session.commit()
    return {'ok': True, 'id': evento.id, 'titulo': evento.titulo}


def atualizar_evento(user_id, evento_id, titulo=None, data_inicio=None, data_fim=None,
                      descricao=None, localizacao=None, cor=None, dia_inteiro=None, notificar=None):
    evento = Evento.query.filter_by(id=evento_id, user_id=user_id).first()
    if not evento:
        return {'erro': 'Evento não encontrado.'}

    inicio = evento.data_inicio
    fim = evento.data_fim
    if data_inicio:
        try:
            inicio = datetime.fromisoformat(data_inicio)
        except ValueError:
            return {'erro': f'Data de início inválida: "{data_inicio}".'}
    if data_fim:
        try:
            fim = datetime.fromisoformat(data_fim)
        except ValueError:
            return {'erro': f'Data de fim inválida: "{data_fim}".'}
    if fim < inicio:
        return {'erro': 'A data de fim não pode ser anterior à data de início.'}

    evento.titulo = titulo or evento.titulo
    evento.descricao = descricao if descricao is not None else evento.descricao
    evento.localizacao = localizacao if localizacao is not None else evento.localizacao
    evento.data_inicio = inicio
    evento.data_fim = fim
    if cor and cor in CORES_EVENTO:
        evento.cor = cor
    if dia_inteiro is not None:
        evento.dia_inteiro = dia_inteiro
    if notificar is not None:
        evento.notificar = notificar
    evento.notificado_em = None  # como na rota — reabre a janela de notificação

    db.session.commit()
    return {'ok': True, 'id': evento.id}


def apagar_evento(user_id, evento_id, confirmado=False):
    evento = Evento.query.filter_by(id=evento_id, user_id=user_id).first()
    if not evento:
        return {'erro': 'Evento não encontrado.'}

    if not confirmado:
        return {
            'confirmacao_necessaria': True,
            'mensagem': f'Confirmas que queres apagar o evento "{evento.titulo}"?',
        }

    db.session.delete(evento)
    db.session.commit()
    return {'ok': True}


# ── Passwords — escrita (stateless) ──────────────────────────────────────

def gerar_credencial(user_id, modo='password', comprimento=16, maiusculas=True, minusculas=True,
                      numeros=True, simbolos=True, excluir_ambiguos=False, num_palavras=4):
    if modo == 'passphrase':
        return gerar_passphrase(num_palavras)
    if modo == 'pin':
        return gerar_pin(comprimento)
    return gerar_password(comprimento, maiusculas, minusculas, numeros, simbolos, excluir_ambiguos)


def executar_ferramenta(nome_ferramenta, argumentos, user_id, modo='leitura'):
    """Despacha a chamada para a função correspondente.

    O user_id é sempre injetado — nunca vem do modelo. Ferramentas de escrita
    só executam em modo='escrita', mesmo que o modelo as invoque por engano.
    """
    func_nome = REGISTO_FERRAMENTAS.get(nome_ferramenta)
    if not func_nome:
        return {'erro': f'Ferramenta desconhecida: {nome_ferramenta}'}

    if nome_ferramenta in FERRAMENTAS_ESCRITA:
        if modo != 'escrita':
            return {'erro': 'Esta acção só está disponível em modo de execução.'}
        if _limite_escrita_excedido():
            return {'erro': 'Limite de acções por minuto atingido. Aguarda um momento e tenta novamente.'}

    func = globals()[func_nome]
    try:
        return func(user_id=user_id, **argumentos) if argumentos else func(user_id=user_id)
    except Exception as e:
        db.session.rollback()
        return {'erro': f'Falha ao executar {nome_ferramenta}: {e}'}
