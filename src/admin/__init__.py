"""
Módulo Admin (Blueprint)

Gerencia as rotas de administração (Upload, Gestão de PDFs).
"""

from flask import Blueprint

admin_bp = Blueprint(
    'admin_bp', 
    __name__,
    static_folder='static',
    url_prefix='/admin' # Todas as rotas começarão com /admin
)

from . import routes