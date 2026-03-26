from datetime import datetime, timezone
from app import db


class Conversao(db.Model):
    """Metadados de conversões HEIC → JPG (sem ficheiros armazenados)."""
    __tablename__ = 'conversoes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)
    num_ficheiros = db.Column(db.Integer, nullable=False)
    tamanho_total_kb = db.Column(db.Integer, nullable=False)
    convertido_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('conversoes', lazy='dynamic'))

    def __repr__(self):
        return f'<Conversao {self.id}: {self.num_ficheiros} ficheiros>'