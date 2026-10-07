"""Provider de resumo do dashboard para o módulo Tarefas."""
from datetime import date, timedelta

from app.dashboard.base import DashboardProvider, Estado, Metrica
from app.tarefas.models import Tarefa


class TarefasProvider(DashboardProvider):
    slug = "tarefas"
    nome = "Tarefas"
    icone = "✅"
    campos = {
        "total": "Total",
        "pendentes": "Pendentes",
        "em_atraso": "Em atraso",
        "concluidas_hoje": "Concluídas hoje",
    }

    def resumir(self, user_id: int) -> dict:
        try:
            hoje = date.today()

            total = Tarefa.query.filter_by(user_id=user_id).count()
            if total == 0:
                return {"estado": Estado.NAO_CONFIGURADO, "metricas": []}

            pendentes = Tarefa.query.filter_by(
                user_id=user_id, concluida=False,
            ).count()

            em_atraso = Tarefa.query.filter(
                Tarefa.user_id == user_id,
                Tarefa.concluida == False,  # noqa: E712
                Tarefa.data_limite != None,  # noqa: E711
                Tarefa.data_limite < hoje,
            ).count()

            concluidas_hoje = Tarefa.query.filter(
                Tarefa.user_id == user_id,
                Tarefa.concluida == True,  # noqa: E712
                Tarefa.data_conclusao != None,  # noqa: E711
                Tarefa.data_conclusao >= hoje,
                Tarefa.data_conclusao < hoje + timedelta(days=1),
            ).count()

            metricas = [
                Metrica("total", total).to_dict(),
                Metrica("pendentes", pendentes).to_dict(),
                Metrica("em_atraso", em_atraso).to_dict(),
                Metrica("concluidas_hoje", concluidas_hoje).to_dict(),
            ]

            return {"estado": Estado.OK, "metricas": metricas, "campos": self.campos}
        except Exception as exc:
            return {"estado": Estado.INDISPONIVEL, "erro": str(exc)}
