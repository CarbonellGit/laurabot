"""
Módulo Principal da Aplicação (Application Factory)
"""

from flask import Flask
from config import Config

# Importa a instância do nosso novo arquivo
from .core.oauth import oauth

def create_app(config_class=Config):
    """
    Cria e configura uma instância da aplicação Flask.
    """
    
    app = Flask(__name__, 
                instance_relative_config=True,
                static_folder='static',
                template_folder='templates')

    # 1. Carrega a configuração (config.py)
    app.config.from_object(config_class)

    # 2. (NOVO) INICIALIZA E CONFIGURA O AUTHLIB
    oauth.init_app(app)
    
    # Pega as credenciais do config
    google_client_id = app.config.get('GOOGLE_CLIENT_ID')
    google_client_secret = app.config.get('GOOGLE_CLIENT_SECRET')

    if google_client_id and google_client_secret:
        # Registra o cliente 'google' (exatamente como no seu app.py de exemplo)
        oauth.register(
            name='google',
            client_id=google_client_id,
            client_secret=google_client_secret,
            # Esta URL mágica busca todas as outras (auth_uri, token_uri)
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                # 'scope' define o que queremos (email e nome)
                'scope': 'openid email profile'
            }
        )
    else:
        print("AVISO: GOOGLE_CLIENT_ID ou GOOGLE_CLIENT_SECRET não definidos no .env")


    # 3. Configura os Blueprints (Módulos)
    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/')

    from .chat import chat_bp
    app.register_blueprint(chat_bp, url_prefix='/')
    
    # (admin_bp... etc)

    # 4. Rota de Health Check
    @app.route("/health")
    def health_check():
        return "Servidor LauraBot no ar!", 200

    return app