"""
Módulo de Autenticação (Blueprint)

Define o Blueprint do Flask para todas as rotas relacionadas
à autenticação de usuários (Login, Logout, Callback).
"""

from flask import Blueprint

# Cria uma instância do Blueprint para 'auth'
auth_bp = Blueprint(
    'auth_bp', 
    __name__,
    template_folder='templates',  # Diz ao Blueprint onde procurar seus templates
    static_folder='static'        # (Opcional, se tivéssemos CSS/JS só de auth)
)

# Importa as rotas no final para evitar dependência circular
from . import routes