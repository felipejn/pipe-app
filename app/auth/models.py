import pyotp

from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    __tablename__ = 'utilizadores'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_login = db.Column(db.DateTime)
    activo = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)

    # 2FA — Telegram
    dois_fa_activo = db.Column(db.Boolean, default=False)
    dois_fa_chat_id = db.Column(db.String(64), nullable=True)

    # 2FA — Email
    dois_fa_email_activo = db.Column(db.Boolean, default=False)

    # 2FA — TOTP (Google Authenticator / Authy)
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_activo = db.Column(db.Boolean, default=False)

    # Código partilhado por Telegram e Email
    dois_fa_codigo = db.Column(db.String(6), nullable=True)
    dois_fa_expira = db.Column(db.DateTime, nullable=True)

    # Recuperação de password
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expira = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def metodos_2fa_activos(self):
        """Devolve lista de métodos 2FA activos para este utilizador."""
        metodos = []
        if self.dois_fa_activo and self.dois_fa_chat_id:
            metodos.append('telegram')
        if self.dois_fa_email_activo:
            metodos.append('email')
        if self.totp_activo and self.totp_secret:
            metodos.append('totp')
        return metodos

    def gerar_totp_secret(self):
        """Gera um novo secret TOTP e guarda no modelo (sem commit)."""
        self.totp_secret = pyotp.random_base32()
        return self.totp_secret

    def totp_uri(self, nome_app='PIPE'):
        """Devolve o URI otpauth:// para gerar o QR code."""
        if not self.totp_secret:
            return None
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.username,
            issuer_name=nome_app
        )

    def verificar_totp(self, codigo):
        """Verifica um código TOTP. Aceita janela de ±1 intervalo (30s)."""
        if not self.totp_secret or not self.totp_activo:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(codigo.strip(), valid_window=1)

    def codigo_valido(self, codigo):
        """Verifica se o código 2FA introduzido é válido e não expirou."""
        if not self.dois_fa_codigo or not self.dois_fa_expira:
            return False
        if datetime.utcnow() > self.dois_fa_expira:
            return False
        return self.dois_fa_codigo == codigo.strip()

    def limpar_codigo(self):
        """Remove o código 2FA após uso ou expiração."""
        self.dois_fa_codigo = None
        self.dois_fa_expira = None

    def __repr__(self):
        return f'<User {self.username}>'


class Convite(db.Model):
    __tablename__ = 'convites'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    expira_em = db.Column(db.DateTime, nullable=False)
    usado = db.Column(db.Boolean, default=False)
    usado_em = db.Column(db.DateTime, nullable=True)

    def esta_valido(self):
        """Verifica se o convite não foi usado e não expirou."""
        return not self.usado and datetime.utcnow() < self.expira_em


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
