"""Modelos: localizacao guardada (Etapa A) e cache da previsao."""
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


class PrevisaoCache(db.Model):
    """Ultima previsao com sucesso por coordenadas (fallback da API).

    Uma linha por localizacao (~1 km de precisao); payload em JSON com o
    mesmo formato devolvido por ``obter_previsao``. Serve o módulo
    Meteorologia, o Assistente e o Resumo Diário quando a Open-Meteo
    está em baixo — nunca mais velho que IDADE_MAXIMA_CACHE_HORAS.
    """

    __tablename__ = 'meteorologia_previsao_cache'

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(32), nullable=False, unique=True, index=True)
    payload = db.Column(db.Text, nullable=False)
    obtida_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                          index=True)

    def __repr__(self):
        return f'<PrevisaoCache {self.chave} obtida_em={self.obtida_em}>'
