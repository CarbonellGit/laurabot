"""
Rotas do Módulo de Autenticação

Gerencia as rotas para /login, /logout, callbacks e cadastro de estudantes.
"""

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


# --- ROTAS DE CADASTRO (RF-004 e RF-005) ---

@auth_bp.route('/cadastro-estudantes')
def cadastro_alunos(): # Mantivemos o nome da função interna por compatibilidade, mas a rota mudou
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    if session['user_profile'].get('possui_cadastro_filhos', False):
        return redirect(url_for('chat_bp.index'))

    return render_template('cadastro_alunos.html')


@auth_bp.route('/salvar-estudantes', methods=['POST'])
def salvar_estudantes():
    """
    RF-005: Processa, higieniza e salva os dados dos estudantes no Firestore.
    """
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    # O formulário envia dados no formato:
    # estudantes[0][nome], estudantes[0][segmento], etc.
    # Precisamos converter isso para uma lista de dicionários Python.
    
    raw_form = request.form
    estudantes_processados = []
    
    # Lógica manual para agrupar os campos do formulário
    # (Existem bibliotecas como WTForms que fazem isso, mas faremos nativo para controle total)
    indices = set()
    for key in raw_form.keys():
        if key.startswith('estudantes['):
            # Extrai o índice (ex: '0' de 'estudantes[0][nome]')
            import re
            match = re.search(r'estudantes\[(\d+)\]', key)
            if match:
                indices.add(int(match.group(1)))
    
    # Para cada índice encontrado, montamos o objeto estudante
    for i in sorted(indices):
        nome_raw = raw_form.get(f'estudantes[{i}][nome]', '')
        
        # --- HIGIENIZAÇÃO DE DADOS (Evitar erros de digitação) ---
        # 1. Strip: Remove espaços em branco no inicio e fim
        # 2. Title: Converte "joao silva" para "Joao Silva"
        nome_limpo = nome_raw.strip().title()
        
        estudante = {
            'nome': nome_limpo,
            'segmento': raw_form.get(f'estudantes[{i}][segmento]'),
            'serie': raw_form.get(f'estudantes[{i}][serie]'),
            'periodo': raw_form.get(f'estudantes[{i}][periodo]')
        }
        estudantes_processados.append(estudante)

    # Validamos se temos pelo menos um estudante
    if not estudantes_processados:
        return "Erro: Nenhum estudante enviado.", 400

    # --- SALVAMENTO NO FIRESTORE (RF-005) ---
    try:
        user_email = session['user_profile']['email']
        
        # Atualiza o documento do responsável
        doc_ref = db.collection('responsaveis').document(user_email)
        
        doc_ref.update({
            'filhos': estudantes_processados, # Mantemos a chave 'filhos' no banco por padrão, ou mudamos para 'estudantes' se preferir
            'possui_cadastro_filhos': True,
            'ano_ultima_atualizacao': 2025 # Define o ano corrente (RF-007.1)
        })
        
        # Atualiza a sessão local também para não precisar relogar
        session['user_profile']['possui_cadastro_filhos'] = True
        session['user_profile']['filhos'] = estudantes_processados
        session.modified = True # Força o Flask a salvar a sessão

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
    
    # Busca dados frescos do banco (importante!)
    dados_atualizados = auth_services.obter_responsavel(email)
    
    if dados_atualizados:
        # Atualiza a sessão também
        session['user_profile'] = dados_atualizados
        estudantes = dados_atualizados.get('filhos', [])
    else:
        estudantes = []

    return render_template('perfil.html', estudantes=estudantes)