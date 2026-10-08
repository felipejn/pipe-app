"""Preferências do Resumo Diário, isoladas por utilizador."""

from app import db


class ConfiguracaoResumoDiario(db.Model):
    __tablename__ = 'resumo_diario_configuracoes'
    __table_args__ = (db.UniqueConstraint('user_id', name='uq_resumo_diario_user'),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)
    meteorologia = db.Column(db.Boolean, nullable=False, default=True, server_default='1')
    tarefas = db.Column(db.Boolean, nullable=False, default=True, server_default='1')
    eventos = db.Column(db.Boolean, nullable=False, default=True, server_default='1')
    combustiveis = db.Column(db.Boolean, nullable=False, default=True, server_default='1')
    fim_de_semana = db.Column(db.Boolean, nullable=False, default=True, server_default='1')
    ultimo_envio = db.Column(db.Date, nullable=True)
