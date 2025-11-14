"""
Rotas do Módulo de Autenticação

Gerencia as rotas para /login, /logout, e os callbacks do Google OAuth.
"""

from flask import render_template
from . import auth_bp  # Importa o Blueprint

@auth_bp.route('/login')
def login():
    """
    Exibe a página de login (RF-001).
    
    Esta página conterá o botão "Fazer login com o Google".
    """
    
    # O 'auth/login.html' virá da pasta 'src/auth/templates/auth/login.html'
    # Mas o Flask já sabe procurar no 'template_folder' do blueprint
    # Vamos criar a página de login no 'src/templates' por enquanto
    # e depois mover se necessário.
    
    # CORREÇÃO: Vamos usar o 'src/templates/login.html' que definimos antes
    
    return render_template('login.html')

# (Vamos adicionar as rotas /google/login e /google/callback aqui na próxima etapa)