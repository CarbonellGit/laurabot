"""
Rotas do Módulo de Autenticação (Refatorado com Authlib)

Gerencia as rotas para /login, /logout, e os callbacks do Google OAuth.
"""

from flask import (
    render_template, 
    redirect, 
    url_for, 
    session, 
    request, 
    current_app,
    abort
)

# Importa a camada de serviço (isso não muda)
from . import services as auth_services

# Importa o Blueprint (isso não muda)
from . import auth_bp  

# (NOVO) Importa a instância do Authlib
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
    """
    (REFATORADO) Redireciona o usuário para a tela de consentimento do Google.
    """
    # Define a URL de callback (o nome da *próxima* função)
    redirect_uri = url_for('auth_bp.google_callback', _external=True)
    
    # Usa o 'oauth.google' (que registramos na factory) para redirecionar
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/google/callback')
def google_callback():
    """
    (REFATORADO) Lida com o retorno do Google após o login.
    """
    try:
        # 1. Pega o token. O Authlib valida o 'state' automaticamente.
        token = oauth.google.authorize_access_token()
        
        # 2. Pega o 'userinfo' (Authlib já faz a requisição)
        # (No seu app.py de exemplo, é 'token.get('userinfo')')
        # A forma mais moderna é:
        user_info = oauth.google.userinfo(token=token)
        # Se isso falhar, usamos a do seu exemplo:
        # user_info = token.get('userinfo') 

        if not user_info:
            print("Erro: Authlib não retornou 'userinfo'.")
            abort(500, "Falha ao obter 'userinfo' do Google.")

        # 3. Prepara o perfil básico (com o ID padrão 'sub')
        google_profile = {
            'email': user_info.get('email'),
            'nome': user_info.get('name'),
            'google_id': user_info.get('sub') # 'sub' é o ID OIDC padrão
        }

        # 4. (RF-002) CHAMA A CAMADA DE SERVIÇO (Nada muda aqui)
        user_data_completo = auth_services.verificar_ou_criar_responsavel(google_profile)
        session['user_profile'] = user_data_completo

    except Exception as e:
        print(f"Erro no callback do Authlib: {e}")
        return redirect(url_for('auth_bp.login'))
    
    
    # 5. (RF-003) Lógica de Redirecionamento (Nada muda aqui)
    if user_data_completo.get('possui_cadastro_filhos', False):
        return redirect(url_for('chat_bp.index'))
    else:
        return redirect(url_for('auth_bp.cadastro_alunos'))


@auth_bp.route('/logout')
def logout():
    session.pop('user_profile', None)
    return redirect(url_for('auth_bp.login'))


# (RF-003) Rota de Cadastro (Ainda sem HTML)
@auth_bp.route('/cadastro-alunos')
def cadastro_alunos():
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    if session['user_profile'].get('possui_cadastro_filhos', False):
        return redirect(url_for('chat_bp.index'))

    return f"Página de Cadastro de Alunos (Em construção) - (RF-004)"