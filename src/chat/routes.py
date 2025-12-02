"""
Rotas do Módulo de Chat (RF-013 a RF-019)
"""

from flask import render_template, session, redirect, url_for
from . import chat_bp

@chat_bp.route('/')
def index():
    """
    Rota principal da aplicação (O Chat).
    
    Verifica se o usuário está logado. Se não, redireciona para /login.
    """
    
    # Proteção de Rota: Verifica se o usuário está na sessão
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    # (Lógica do RF-003)
    # Se o usuário está logado, mas não cadastrou os filhos,
    # força o redirecionamento para o cadastro.
    if not session['user_profile'].get('possui_cadastro_filhos', False):
         return redirect(url_for('auth_bp.cadastro_alunos'))


    # Se estiver tudo certo, renderiza a página do chat
    # (Vamos criar o 'chat.html' em breve)
    user_nome = session['user_profile'].get('nome', 'Usuário')
    return f"Página do Chat (Em construção). Bem-vindo, {user_nome}!"
    
    # return render_template('chat.html')