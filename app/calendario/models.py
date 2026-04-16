from app import db
from datetime import datetime

class Evento(db.Model):
    __tablename__ = 'evento'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)
    titulo        = db.Column(db.String(200), nullable=False)
    descricao     = db.Column(db.Text, nullable=True)
    localizacao   = db.Column(db.String(300), nullable=True)
    data_inicio   = db.Column(db.DateTime, nullable=False)
    data_fim      = db.Column(db.DateTime, nullable=False)
    dia_inteiro   = db.Column(db.Boolean, default=False)
    cor           = db.Column(db.String(20), default='tomate')
    notificar     = db.Column(db.Boolean, default=True)
    notificado_em = db.Column(db.Date, nullable=True)
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)
