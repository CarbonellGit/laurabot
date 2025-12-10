"""
Módulo Principal da Aplicação (Application Factory)
"""

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix # Importação necessária para o Cloud Run
from config import Config

# Importa a instância do oauth
from .core.constants import DADOS_ESCOLA
from .core.oauth import oauth

def create_app(config_class=Config):
    """
    Cria e configura uma instância da aplicação Flask.
    """
    
    app = Flask(__name__, 
                instance_relative_config=True,
                static_folder='static',
                template_folder='templates')

    # === CORREÇÃO HTTPS (Cloud Run) ===
    # Ajusta o Flask para entender que está atrás de um Proxy (Cloud Run)
    # Isso garante que ele gere URLs com 'https://' em vez de 'http://'
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    # ==================================

    # 1. Carrega a configuração
    app.config.from_object(config_class)

    # 2. Inicializa o Authlib
    oauth.init_app(app)
    
    google_client_id = app.config.get('GOOGLE_CLIENT_ID')
    google_client_secret = app.config.get('GOOGLE_CLIENT_SECRET')

    if google_client_id and google_client_secret:
        oauth.register(
            name='google',
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
    else:
        print("AVISO: GOOGLE_CLIENT_ID ou GOOGLE_CLIENT_SECRET não definidos.")

    # === NOVO: Context Processor ===
    # Isso injeta 'DADOS_ESCOLA' em todos os templates HTML automaticamente.
    @app.context_processor
    def inject_school_data():
        return dict(DADOS_ESCOLA_GLOBAL=DADOS_ESCOLA)


    # 3. Configura os Blueprints (Módulos)
    
    # Módulo de Autenticação
    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/')

    # Módulo de Chat
    from .chat import chat_bp
    app.register_blueprint(chat_bp, url_prefix='/')
    
    # Módulo Admin (NOVO)
    # O url_prefix='/admin' já está definido dentro do admin/__init__.py
    from .admin import admin_bp
    app.register_blueprint(admin_bp)

    # 4. Rota de Health Check
    @app.route("/health")
    def health_check():
        return "Servidor LauraBot no ar!", 200

    return app