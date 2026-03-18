from flask import Flask, app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sessão para aceder a esta página.'
login_manager.login_message_category = 'info'

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

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

    # Rota raiz — redireciona para dashboard
    from flask import redirect, url_for
    from flask_login import login_required

    @app.route('/')
    @login_required
    def dashboard():
        from flask import render_template
        return render_template('dashboard.html')

    # Criar tabelas se não existirem
    with app.app_context():
        from app.notifications.models import UserNotificationPreferences  # noqa: F401
        from app.tarefas.models import Lista, Tarefa, TagTarefa  # noqa: F401
        from app.notas.models import Nota, ItemChecklist, EtiquetaNota  # noqa: F401
        db.create_all()

    return app
