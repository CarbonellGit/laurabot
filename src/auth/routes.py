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
from .forms import CadastroAlunosForm

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

    # Inicializa o form (necessário para o CSRF token)
    form = CadastroAlunosForm()
    return render_template('cadastro_alunos.html', form=form)


@auth_bp.route('/salvar-estudantes', methods=['POST'])
def salvar_estudantes():
    """
    RF-005: Processa, valida e salva os dados dos estudantes usando WTForms.
    """
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    form = CadastroAlunosForm()
    
    # Valida o formulário completo
    if form.validate_on_submit():
        estudantes_processados = []
        
        for estudante_form in form.estudantes:
            # WTForms já validou os tipos e required
            dados = {
                'nome': estudante_form.nome.data.strip().title(),
                'segmento': estudante_form.segmento.data,
                'serie': estudante_form.serie.data,
                'periodo': estudante_form.periodo.data,
                'turma': estudante_form.turma.data,
                'integral': estudante_form.integral.data
            }
            estudantes_processados.append(dados)

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
                'ano_ultima_atualizacao': 2025
            })
            
            # Atualiza a sessão local
            session['user_profile']['possui_cadastro_filhos'] = True
            session['user_profile']['filhos'] = estudantes_processados
            session.modified = True 

            return redirect(url_for('chat_bp.index'))

        except Exception as e:
            print(f"Erro ao salvar estudantes: {e}")
            return f"Erro ao salvar: {e}", 500
    
    else:
        # Se falhar na validação, retorna erros
        # Idealmente, renderizaria o template com os erros, 
        # mas como é dinâmico via JS, vamos retornar erro 400 por enquanto
        # ou redirecionar com flash.
        return f"Erro de Validação: {form.errors}", 400
    
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

    # Passamos o form vazio apenas para gerar o CSRF Token
    form = CadastroAlunosForm()
    return render_template('perfil.html', estudantes=estudantes, form=form)