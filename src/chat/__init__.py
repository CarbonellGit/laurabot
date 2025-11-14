"""
Módulo do Chat (Blueprint)

Define o Blueprint do Flask para a interface principal do chatbot.
"""

from flask import Blueprint

chat_bp = Blueprint(
    'chat_bp', 
    __name__,
    template_folder='templates',
    static_folder='static'
)

# Importa as rotas no final
from . import routes