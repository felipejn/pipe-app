"""Ferramentas de tool use — funções que o modelo de IA pode invocar.

Cada função recebe user_id e filtra TODAS as queries por esse valor
ao nível de Python/SQLAlchemy. Este filtro é inegociável.
"""

from datetime import date

from app.tarefas.models import Lista, Tarefa
from app.notas.models import EtiquetaNota, Nota
from app.euromilhoes.models import Jogo


# ── Definições de ferramentas (formato OpenAI Function Calling) ──────────────────

DEFINICOES_FERRAMENTAS = [
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
]

# Mapa nome → função executável
REGISTO_FERRAMENTAS = {
    'get_tarefas': 'get_tarefas',
    'get_notas': 'get_notas',
    'get_euromilhoes': 'get_euromilhoes',
    'get_resumo_geral': 'get_resumo_geral',
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


def executar_ferramenta(nome_ferramenta, argumentos, user_id):
    """Despacha a chamada para a função correspondente ao nome recebido.

    O user_id é sempre injetado como primeiro argumento — nunca vem do modelo.

    Args:
        nome_ferramenta: str com o nome da função (ex: 'get_tarefas').
        argumentos: dict com os argumentos extraídos do tool_call.
        user_id: ID do utilizador autenticado (injetado pelo caller).

    Returns:
        O resultado da função chamada, ou mensagem de erro.
    """
    func_nome = REGISTO_FERRAMENTAS.get(nome_ferramenta)
    if not func_nome:
        return f'[Ferramenta desconhecida: {nome_ferramenta}]'

    func = globals()[func_nome]
    return func(user_id=user_id, **argumentos) if argumentos else func(user_id=user_id)
