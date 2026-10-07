"""Modelo da localizacao guardada (Etapa A — uma por utilizador)."""
from datetime import datetime

from app import db


class LocalizacaoMeteorologia(db.Model):
    """Localizacao escolhida pelo utilizador para a previsao."""

    __tablename__ = 'meteorologia_localizacao'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('utilizadores.id'),
        nullable=False, unique=True)
    nome = db.Column(db.String(120), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    pais = db.Column(db.String(80), nullable=False)
    regiao = db.Column(db.String(120), nullable=True)
    timezone = db.Column(db.String(64), nullable=True, default='Europe/Lisbon')
    atualizada_em = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<LocalizacaoMeteorologia {self.nome} user={self.user_id}>'
