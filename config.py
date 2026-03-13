import os
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

    # Sessões
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True  # HTTPS obrigatório no PA

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
