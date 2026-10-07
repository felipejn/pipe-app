"""Registry explícito dos providers de resumos do dashboard.

Lista explícita e auditável — nada de auto-registo por import do blueprint.
A associação das classes é feita uma única vez em create_app() via
`carregar_providers()`. Módulos sem provider ficam fora do dict e continuam
a aparecer no dashboard como cards clássicos (fallback).
"""

from app.dashboard.base import DashboardProvider


# Registry vazio até a factory chamar `carregar_providers()`.
DASHBOARD_PROVIDERS: dict[str, DashboardProvider] = {}


def carregar_providers() -> None:
    """Associa os providers registados ao dict `DASHBOARD_PROVIDERS`.

    Esta função é importada e chamada uma única vez dentro de
    `app.create_app()`, logo após o registo dos blueprints. Não executa
    queries nem faz chamadas externas — apenas carrega as classes.

    Usa .clear() + .update() em vez de reatribuição para preservar
    referências existentes de `from registry import DASHBOARD_PROVIDERS`.
    """
    from app.calendario.dashboard import CalendarioProvider
    from app.tarefas.dashboard import TarefasProvider

    DASHBOARD_PROVIDERS.clear()
    DASHBOARD_PROVIDERS.update({
        "tarefas": TarefasProvider(),
        "calendario": CalendarioProvider(),
    })

