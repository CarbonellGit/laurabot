"""
Rotas do Módulo de Autenticação

Gerencia as rotas para /login, /logout, e os callbacks do Google OAuth.
"""

from flask import (
    render_template, 
    redirect, 
    url_for, 
    session, 
    abort
)

from . import services as auth_services
from . import auth_bp  
from src.core.oauth import oauth


@auth_bp.route('/login')
def login():
    """ Exibe a página de login (RF-001). """
    if 'user_profile' in session:
        if session['user_profile'].get('possui_cadastro_filhos', False):
            return redirect(url_for('chat_bp.index'))
        else:
            return redirect(url_for('auth_bp.cadastro_alunos'))

    return render_template('login.html')


@auth_bp.route('/google/login')
def google_login():
    """ Redireciona para o Google. """
    redirect_uri = url_for('auth_bp.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/google/callback')
def google_callback():
    """ Retorno do Google após login. """
    try:
        token = oauth.google.authorize_access_token()
        user_info = oauth.google.userinfo(token=token)

        if not user_info:
            abort(500, "Falha ao obter dados do Google.")

        google_profile = {
            'email': user_info.get('email'),
            'nome': user_info.get('name'),
            'google_id': user_info.get('sub')
        }

        # Verifica/Cria no Firestore
        user_data_completo = auth_services.verificar_ou_criar_responsavel(google_profile)
        
        # Salva na sessão (Agora sem o erro de JSON!)
        session['user_profile'] = user_data_completo

    except Exception as e:
        print(f"Erro no login: {e}")
        return redirect(url_for('auth_bp.login'))
    
    # Redirecionamento (RF-003)
    if user_data_completo.get('possui_cadastro_filhos', False):
        return redirect(url_for('chat_bp.index'))
    else:
        return redirect(url_for('auth_bp.cadastro_alunos'))


@auth_bp.route('/logout')
def logout():
    session.pop('user_profile', None)
    return redirect(url_for('auth_bp.login'))


@auth_bp.route('/cadastro-alunos')
def cadastro_alunos():
    # Proteção de rota
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    # Se já tem cadastro, manda pro chat
    if session['user_profile'].get('possui_cadastro_filhos', False):
        return redirect(url_for('chat_bp.index'))

    # Por enquanto, retorna apenas texto. Próximo passo: Criar o HTML.
    return "SUCESSO! Você está logado e na tela de Cadastro de Alunos (RF-004)."