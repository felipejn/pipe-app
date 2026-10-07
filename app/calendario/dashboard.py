"""Provider de resumo do dashboard para o módulo Calendário."""
import datetime
from datetime import date, timedelta

from app.dashboard.base import DashboardProvider, Estado, Metrica
from app.calendario.models import Evento


class CalendarioProvider(DashboardProvider):
    slug = "calendario"
    nome = "Calendário"
    icone = "📅"
    campos = {
        "hoje": "Hoje",
        "proximos_7_dias": "Próximos 7 dias",
        "total": "Total",
    }

    def resumir(self, user_id: int) -> dict:
        try:
            hoje = date.today()
            fim_semana = hoje + timedelta(days=7)

            total = Evento.query.filter_by(user_id=user_id).count()
            if total == 0:
                return {"estado": Estado.NAO_CONFIGURADO, "metricas": []}

            hoje_start = datetime.datetime.combine(hoje, datetime.time.min)
            hoje_end = datetime.datetime.combine(hoje, datetime.time.max)

            eventos_hoje = Evento.query.filter(
                Evento.user_id == user_id,
                Evento.data_inicio >= hoje_start,
                Evento.data_inicio <= hoje_end,
            ).count()

            proximos = Evento.query.filter(
                Evento.user_id == user_id,
                Evento.data_inicio >= hoje_start,
                Evento.data_inicio <= datetime.datetime.combine(fim_semana, datetime.time.max),
            ).count()

            metricas = [
                Metrica("hoje", eventos_hoje).to_dict(),
                Metrica("proximos_7_dias", proximos).to_dict(),
                Metrica("total", total).to_dict(),
            ]

            return {"estado": Estado.OK, "metricas": metricas, "campos": self.campos}
        except Exception as exc:
            return {"estado": Estado.INDISPONIVEL, "erro": str(exc)}
