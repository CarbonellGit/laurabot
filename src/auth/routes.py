"""
Rotas do Módulo de Autenticação

Gerencia as rotas para /login, /logout, callbacks e cadastro de estudantes.
"""

import re
from flask import (
    render_template, 
    redirect, 
    url_for, 
    session, 
    abort,
    request
)

from . import services as auth_services
from . import auth_bp  
from src.core.oauth import oauth
from src.core.database import db

# === ROTAS DE LOGIN/LOGOUT (RF-001) ===

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

        user_data_completo = auth_services.verificar_ou_criar_responsavel(google_profile)
        session['user_profile'] = user_data_completo

    except Exception as e:
        print(f"Erro no login: {e}")
        return redirect(url_for('auth_bp.login'))
    
    if user_data_completo.get('possui_cadastro_filhos', False):
        return redirect(url_for('chat_bp.index'))
    else:
        return redirect(url_for('auth_bp.cadastro_alunos'))


@auth_bp.route('/logout')
def logout():
    session.pop('user_profile', None)
    return redirect(url_for('auth_bp.login'))


# === ROTAS DE CADASTRO (RF-004 e RF-005) ===

@auth_bp.route('/cadastro-estudantes')
def cadastro_alunos(): 
    """ Exibe o formulário de primeiro cadastro. """
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    if session['user_profile'].get('possui_cadastro_filhos', False):
        return redirect(url_for('chat_bp.index'))

    return render_template('cadastro_alunos.html')


@auth_bp.route('/salvar-estudantes', methods=['POST'])
def salvar_estudantes():
    """
    RF-005: Processa, higieniza e salva os dados dos estudantes no Firestore.
    Inclui lógica para o campo 'Integral'.
    """
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    # O formulário envia dados no formato: estudantes[0][nome], estudantes[0][segmento], etc.
    raw_form = request.form
    estudantes_processados = []
    
    # 1. Identifica quais índices (0, 1, 2...) foram enviados
    indices = set()
    for key in raw_form.keys():
        if key.startswith('estudantes['):
            # Extrai o número entre colchetes
            match = re.search(r'estudantes\[(\d+)\]', key)
            if match:
                indices.add(int(match.group(1)))
    
    # 2. Processa cada estudante encontrado
    for i in sorted(indices):
        nome_raw = raw_form.get(f'estudantes[{i}][nome]', '')
        
        # --- Higienização ---
        nome_limpo = nome_raw.strip().title()
        
        # --- Campo Integral ---
        # Checkbox HTML: se marcado envia 'on', se não marcado não envia nada (None)
        integral_check = raw_form.get(f'estudantes[{i}][integral]')
        is_integral = True if integral_check == 'on' else False

        estudante = {
            'nome': nome_limpo,
            'segmento': raw_form.get(f'estudantes[{i}][segmento]'),
            'serie': raw_form.get(f'estudantes[{i}][serie]'),
            'periodo': raw_form.get(f'estudantes[{i}][periodo]'),
            'turma': raw_form.get(f'estudantes[{i}][turma]'),
            'integral': is_integral  # Novo campo salvo no banco
        }
        estudantes_processados.append(estudante)

    # Validamos se temos pelo menos um estudante
    if not estudantes_processados:
        return "Erro: Nenhum estudante enviado.", 400

    # --- Salvamento no Firestore ---
    try:
        user_email = session['user_profile']['email']
        
        # Atualiza o documento do responsável
        doc_ref = db.collection('responsaveis').document(user_email)
        
        doc_ref.update({
            'filhos': estudantes_processados, 
            'possui_cadastro_filhos': True,
            'ano_ultima_atualizacao': 2025 # Define o ano corrente (RF-007.1)
        })
        
        # Atualiza a sessão local também para não precisar relogar
        session['user_profile']['possui_cadastro_filhos'] = True
        session['user_profile']['filhos'] = estudantes_processados
        session.modified = True 

        return redirect(url_for('chat_bp.index'))

    except Exception as e:
        print(f"Erro ao salvar estudantes: {e}")
        return f"Erro ao salvar: {e}", 500
    
@auth_bp.route('/perfil')
def perfil():
    """
    Exibe a tela de edição de cadastro (RF-007).
    """
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    email = session['user_profile']['email']
    
    # Busca dados frescos do banco para popular o form de edição
    dados_atualizados = auth_services.obter_responsavel(email)
    
    if dados_atualizados:
        session['user_profile'] = dados_atualizados
        estudantes = dados_atualizados.get('filhos', [])
    else:
        estudantes = []

    return render_template('perfil.html', estudantes=estudantes)