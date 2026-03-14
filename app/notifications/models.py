from app import db
from datetime import datetime


class UserNotificationPreferences(db.Model):
    """Preferências de notificação por utilizador."""

    __tablename__ = 'notificacao_preferencias'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'),
                        nullable=False, unique=True)

    # Telegram
    telegram_activo = db.Column(db.Boolean, default=False)
    telegram_chat_id = db.Column(db.String(64), nullable=True)

    # Email
    email_activo = db.Column(db.Boolean, default=False)

    # Tipos de notificação
    notificar_resultados = db.Column(db.Boolean, default=True)

    data_actualizacao = db.Column(db.DateTime, default=datetime.utcnow,
                                  onupdate=datetime.utcnow)

    utilizador = db.relationship('User', backref=db.backref(
        'notificacao_prefs', uselist=False, lazy='joined'
    ))

    def __repr__(self):
        return f'<NotifPrefs user_id={self.user_id}>'
