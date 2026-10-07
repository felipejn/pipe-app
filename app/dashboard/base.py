"""Contrato do provider de resumos do dashboard.

Provider = adaptador fino sobre a query/serviço existente do módulo.
Recebe apenas `user_id` (nunca do browser) e devolve contagens /
booleanos, nada de payloads nem de dados sensíveis.

Regras:
- Nenhuma chamada HTTP externa (`requests`/`urllib`) — carga síncrona de `/`.
- Falhas internas viram `Estado.INDISPONIVEL`; "utilizador sem dados" =
  `Estado.NAO_CONFIGURADO`.
- Sempre filtra por `user_id`; nunca propaga exceções para o template.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping


class Estado:
    OK = "ok"
    NAO_CONFIGURADO = "nao_configurado"
    INDISPONIVEL = "indisponivel"


class Metrica:
    """Uma métrica única: {label, valor}."""

    def __init__(self, label: str, valor) -> None:
        self.label = label
        self.valor = valor

    def to_dict(self) -> dict:
        return {"label": self.label, "valor": self.valor}


class DashboardProvider(ABC):
    """Contrato implementado por um provider por módulo.

    Atributos de classe:
        slug  -- identificador em MODULOS_DISPONIVEIS (ex: "tarefas")
        nome  -- nome a exibir no card
        icone -- emoji de MODULOS_DISPONIVEIS

    Campos: mapeamento key -> label amigável para a grelha de métricas.
    """

    slug: str
    nome: str
    icone: str
    campos: Mapping[str, str]

    @abstractmethod
    def resumir(self, user_id: int) -> dict:
        """Retorna o resumo do módulo para um utilizador.

        Estrutura devolvida (sempre):
            {
                "estado": Estado.OK | Estado.NAO_CONFIGURADO | Estado.INDISPONIVEL,
                "metricas": [{"label": ..., "valor": ...}, ...],
                ...: campos adicionais que o template respeita,
            }
        """
