import os
from datetime import timedelta
from flask import Flask, app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from flask_session import Session
from flask_cors import CORS
from app.extensions import limiter
from config import config, BASE_DIR

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sessão para aceder a esta página.'
login_manager.login_message_category = 'info'

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # Configurações de sessão para PWA.
    # SESSION_COOKIE_SAMESITE / SESSION_COOKIE_SECURE vêm das classes de config
    # (Development: Lax/False; Production: None/True) — a extensão Chrome faz
    # pedidos cross-site e só recebe o cookie com SameSite=None (exige HTTPS),
    # pelo que não podem ser fixados aqui.
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

    # Sessões server-side para o cofre (chave nunca no browser).
    # setdefault: a config carregada (ex.: TestingConfig) tem de poder fixar o
    # seu próprio SESSION_FILE_DIR — estes valores são lidos por Session(app)
    # logo a seguir e não podem ser sobrepostos.
    app.config.setdefault('SESSION_TYPE', 'filesystem')
    app.config.setdefault('SESSION_FILE_DIR', os.path.join(BASE_DIR, 'instance', 'flask_session'))
    app.config.setdefault('SESSION_FILE_THRESHOLD', 500)
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    Session(app)

    # Parse de COFRE_CORS_ORIGINS
    _cofre_origins_env = app.config.get('COFRE_CORS_ORIGINS', '')
    _cofre_origins = [o.strip() for o in _cofre_origins_env.split(',') if o.strip()] if _cofre_origins_env else []

    if _cofre_origins:
        CORS(app, resources={
            r"/passwords/api/cofre/*": {"origins": _cofre_origins, "supports_credentials": True},
            r"/passwords/api/csrf-token": {"origins": _cofre_origins, "supports_credentials": True},
        })

    # Inicializar extensões
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Registar blueprints
    from app.auth import auth as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.euromilhoes import euromilhoes as euro_bp
    app.register_blueprint(euro_bp, url_prefix='/euromilhoes')

    from app.settings import settings as settings_bp
    app.register_blueprint(settings_bp, url_prefix='/definicoes')

    from app.admin import admin as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.tarefas import tarefas as tarefas_bp
    app.register_blueprint(tarefas_bp, url_prefix='/tarefas')

    from app.notas import notas as notas_bp
    app.register_blueprint(notas_bp, url_prefix='/notas')

    from app.passwords import bp as passwords_bp
    app.register_blueprint(passwords_bp, url_prefix='/passwords')

    from app.conversoes import bp as conversoes_bp
    app.register_blueprint(conversoes_bp, url_prefix='/conversoes')

    from app.cambio import bp as cambio_bp
    app.register_blueprint(cambio_bp, url_prefix='/cambio')

    from app.cores import bp as cores_bp
    app.register_blueprint(cores_bp, url_prefix='/cores')

    from app.assistente import assistente as assistente_bp
    app.register_blueprint(assistente_bp)

    from app.modulos import modulos_bp
    app.register_blueprint(modulos_bp)

    from app.calendario import calendario_bp
    app.register_blueprint(calendario_bp, url_prefix='/calendario')

    from app.combustiveis import bp as combustiveis_bp
    app.register_blueprint(combustiveis_bp)

    # Limiter inicializado após blueprints — necessário para decoradores funcionarem
    limiter.init_app(app)

    # Security headers
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Rota raiz — redireciona para dashboard
    from flask import redirect, url_for
    from flask_login import login_required

    @app.route('/')
    @login_required
    def dashboard():
        from flask import render_template
        from app.modulos.models import get_modulos_ativos
        from app.modulos.config import MODULOS_DISPONIVEIS
        
        modulos_ativos_slugs = get_modulos_ativos(current_user.id)
        modulos_ativos = []
        for slug in modulos_ativos_slugs:
            if slug in MODULOS_DISPONIVEIS:
                info = MODULOS_DISPONIVEIS[slug]
                modulos_ativos.append({
                    'slug': slug,
                    'nome': info['nome'],
                    'icone': info['icone'],
                    'url_endpoint': info['url_endpoint'],
                    'descricao': info['descricao']
                })
        
        return render_template('dashboard.html', modulos_ativos=modulos_ativos, MODULOS_DISPONIVEIS=MODULOS_DISPONIVEIS)

    # Criar tabelas se não existirem
    with app.app_context():
        from app.passwords.models import CofrePassword, CofreConfig
        from app.notifications.models import UserNotificationPreferences  # noqa: F401
        from app.tarefas.models import Lista, Tarefa, TagTarefa  # noqa: F401
        from app.notas.models import Nota, ItemChecklist, EtiquetaNota  # noqa: F401
        from app.conversoes.models import Conversao  # noqa: F401
        from app.auth.models import Convite  # noqa: F401
        from app.calendario.models import Evento  # noqa: F401
        from app.combustiveis.models import Posto, PrecoHistorico, UtilizadorConcelho, UtilizadorCombustivel, EstadoAtualizacaoCombustiveis  # noqa: F401
        db.create_all()

        # Regra: uma só linha (id=1) na tabela EstadoAtualizacaoCombustiveis
        from app.combustiveis.models import EstadoAtualizacaoCombustiveis
        if EstadoAtualizacaoCombustiveis.query.get(1) is None:
            db.session.add(EstadoAtualizacaoCombustiveis(id=1))
            db.session.commit()

    return app