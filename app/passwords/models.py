from datetime import datetime
from app import db


def extrair_dominio(url):
    """Normaliza e extrai o domínio de uma URL.

    Única fonte de verdade para deduplicação e lookup.
    - urlparse(url).hostname (não netloc — exclui porta e user-info)
    - .lower()
    - strip de 'www.'

    Exemplo: 'https://www.Exemplo.com:8080/user' -> 'exemplo.com'
    """
    from urllib.parse import urlparse
    if not url:
        return None
    hostname = urlparse(url).hostname
    if not hostname:
        return None
    dominio = hostname.lower().strip()
    if dominio.startswith('www.'):
        dominio = dominio[4:]
    return dominio


class CofreConfig(db.Model):
    __tablename__ = 'cofre_configs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), unique=True, nullable=False)
    master_pw_hash = db.Column(db.String(256), nullable=False)
    salt = db.Column(db.String(64), nullable=False)  # base64-encoded
    kdf_iterations = db.Column(db.Integer, default=600000)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CofreConfig user_id={self.user_id}>'


class CofrePassword(db.Model):
    __tablename__ = 'cofre_passwords'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), index=True, nullable=False)
    titulo = db.Column(db.String(128), nullable=True)
    url = db.Column(db.String(512), nullable=True)
    dominio = db.Column(db.String(256), nullable=True, index=True)
    username = db.Column(db.String(256), nullable=True)
    password_cifrada = db.Column(db.LargeBinary, nullable=False)
    iv = db.Column(db.LargeBinary, nullable=False)  # 12 bytes
    tag = db.Column(db.LargeBinary, nullable=False)  # 16 bytes
    notas = db.Column(db.Text, nullable=True)
    favorito = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<CofrePassword id={self.id} user_id={self.user_id} titulo={self.titulo}>'

    def para_dict(self, chave_derivada=None):
        """Devolve dicionário com dados da entrada.

        Se chave_derivada for fornecida, decifra e inclui password em claro.
        """
        from app.passwords.crypto import decifrar
        resultado = {
            'id': self.id,
            'titulo': self.titulo,
            'url': self.url,
            'dominio': self.dominio,
            'username': self.username,
            'notas': self.notas,
            'favorito': self.favorito,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None,
        }
        if chave_derivada and self.password_cifrada:
            try:
                resultado['password'] = decifrar(
                    chave_derivada,
                    bytes(self.password_cifrada),
                    bytes(self.iv),
                    bytes(self.tag)
                )
            except Exception:
                resultado['password'] = None
        return resultado
