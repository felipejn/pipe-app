import os
import tempfile
from dotenv import load_dotenv

# Carrega variáveis do ficheiro .env (se existir)
load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), '.env'))

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Segurança
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-alterar-em-producao'
    WTF_CSRF_ENABLED = True

    # Base de dados
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'pipe.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Notificações — Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

    # Notificações — Mailjet
    # Obter em: https://app.mailjet.com/settings/api_keys
    MAILJET_API_KEY = os.environ.get('MAILJET_API_KEY')
    MAILJET_API_SECRET = os.environ.get('MAILJET_API_SECRET')
    MAILJET_FROM_EMAIL = os.environ.get('MAILJET_FROM_EMAIL')

    # Sessões
    SESSION_COOKIE_HTTPONLY = True
    # Lax por omissão (dev). Em produção passa a None, porque a extensão Chrome
    # faz pedidos cross-site (origem chrome-extension://) e o browser não envia
    # cookies Lax nesses pedidos — sem isto a extensão não fica autenticada.
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora

    # --- Cofre ---
    COFRE_KDF_ITERATIONS = 600000
    COFRE_SESSION_TIMEOUT = 900  # 15 minutos
    COFRE_CORS_ORIGINS = os.environ.get('COFRE_CORS_ORIGINS', '')  # "chrome-extension://abc123,chrome-extension://def456"

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # HTTPS obrigatório no PA
    # SameSite=None é obrigatório para a extensão Chrome (pedidos cross-site a
    # partir de chrome-extension://); exige Secure=True (HTTPS), garantido acima.
    # O CSRF continua protegido pelo token do Flask-WTF em todos os POSTs.
    SESSION_COOKIE_SAMESITE = 'None'

class TestingConfig(Config):
    """Configuração dos testes unitários — isolada da BD real.

    IMPORTANTE: tudo o que é lido em `create_app()` por `db.init_app()` e por
    `Session(app)` tem de estar definido AQUI. Configuração aplicada depois
    dessas chamadas não tem qualquer efeito (o engine do SQLAlchemy e a
    interface de sessão ficam fixados) — foi essa a causa de uma corrida de
    testes com `db.drop_all()` ter apagado todas as tabelas de
    `instance/pipe.db`.

    Usa SQLite em memória e sessões Flask-Session numa pasta temporária, pelo
    que nenhum teste escreve em `instance/`.
    """
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

    # Cofre — sem extensões Chrome autorizadas nos testes
    COFRE_CORS_ORIGINS = ''

    # Sessões server-side isoladas (nunca em instance/flask_session/)
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = tempfile.mkdtemp(prefix='pipe-test-session-')


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
