"""
Módulo Principal da Aplicação (Application Factory)

Este arquivo contém a função create_app(), que é o padrão "Application Factory"
usado para inicializar e configurar a aplicação Flask.
"""

from flask import Flask
from config import Config

def create_app(config_class=Config):
    """
    Cria e configura uma instância da aplicação Flask.

    Args:
        config_class (Config): A classe de configuração a ser usada. 
                               Padrão é a classe 'Config' de config.py.

    Returns:
        Flask: A instância da aplicação Flask configurada.
    """
    
    # Inicializa a aplicação Flask
    # 'instance_relative_config=True' nos permite ter configs na pasta 'instance' (fora do src)
    app = Flask(__name__, 
                instance_relative_config=True,
                static_folder='static',        # Define a pasta de assets estáticos
                template_folder='templates')   # Define a pasta de templates HTML

    # 1. Carrega a configuração a partir do objeto (config.py)
    app.config.from_object(config_class)

    # 2. Configura os Blueprints (Módulos)
    # (Descomentaremos e registraremos quando criarmos os módulos)
    # from .auth import auth_bp
    # app.register_blueprint(auth_bp, url_prefix='/auth')

    # REGISTRA O MÓDULO DE AUTENTICAÇÃO
    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/') # Usamos '/' como prefixo
    
    # from .admin import admin_bp
    # app.register_blueprint(admin_bp, url_prefix='/admin')
    #
    # from .chat import chat_bp
    # app.register_blueprint(chat_bp, url_prefix='/')

    # 3. Adiciona uma rota de "Health Check" (Verificação de Saúde)
    # Isso nos ajuda a verificar se o servidor está no ar.
    @app.route("/health")
    def health_check():
        """Rota simples para verificar se a API está online."""
        return "Servidor LauraBot no ar!", 200

    # Retorna a aplicação criada
    return app