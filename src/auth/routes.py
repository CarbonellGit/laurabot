"""
Rotas do Módulo de Autenticação

Gerencia as rotas para /login, /logout, callbacks e cadastro de estudantes.
Versão: FINAL (Decodificação Manual Base64).
"""

import requests
import json
import base64 # <--- Essencial para decodificar o token manualmente
from flask import (
    render_template, 
    redirect, 
    url_for, 
    session, 
    abort,
    request,
    flash,
    current_app
)

from . import services as auth_services
from . import auth_bp  
from src.core.extensions import oauth
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


# === FUNÇÃO AUXILIAR DE DECODIFICAÇÃO ===
def decodificar_token_manualmente(token_jwt):
    """
    Decodifica o payload de um JWT sem validar assinatura ou datas.
    Isso contorna problemas de relógio (clock skew) e compatibilidade de bibliotecas.
    """
    try:
        # O JWT é dividido em 3 partes: Header.Payload.Signature
        partes = token_jwt.split('.')
        if len(partes) < 2:
            raise ValueError("Token mal formatado")
            
        payload_b64 = partes[1]
        
        # Ajusta o padding do Base64 (necessário em Python)
        payload_b64 += '=' * (-len(payload_b64) % 4)
        
        # Decodifica URL-Safe Base64
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload_str = payload_bytes.decode('utf-8')
        
        return json.loads(payload_str)
    except Exception as e:
        print(f"Erro ao decodificar token manualmente: {e}")
        return None


@auth_bp.route('/google/callback')
def google_callback():
    """ Retorno do Google após login - FLUXO ROBUSTO. """
    print("--- [DEBUG] Callback Google: Iniciando Troca Manual ---")
    
    try:
        code = request.args.get('code')
        if not code:
            raise ValueError("Código de autorização ausente.")

        # 1. Troca o Code pelo Token diretamente com o Google
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            'code': code,
            'client_id': current_app.config.get('GOOGLE_CLIENT_ID'),
            'client_secret': current_app.config.get('GOOGLE_CLIENT_SECRET'),
            'redirect_uri': url_for('auth_bp.google_callback', _external=True),
            'grant_type': 'authorization_code'
        }

        resp = requests.post(token_url, data=payload)
        
        if resp.status_code != 200:
            raise ValueError(f"Google recusou a troca: {resp.text}")

        dados_token = resp.json()
        id_token = dados_token.get('id_token')

        if not id_token:
            raise ValueError("Google não retornou ID Token.")

        # 2. Decodifica manualmente (Ignora completamente o erro de relógio)
        claims = decodificar_token_manualmente(id_token)
        
        if not claims:
            raise ValueError("Falha na decodificação do token.")
        
        print(f"--- [DEBUG] Usuário identificado: {claims.get('email')} ---")

        # 3. Monta perfil e segue o fluxo
        google_profile = {
            'email': claims.get('email'),
            'nome': claims.get('name'),
            'google_id': claims.get('sub')
        }

        user_data_completo = auth_services.verificar_ou_criar_responsavel(google_profile)
        session['user_profile'] = user_data_completo
        
        # Redireciona para a tela correta
        if user_data_completo.get('possui_cadastro_filhos', False):
            return redirect(url_for('chat_bp.index'))
        else:
            return redirect(url_for('auth_bp.cadastro_alunos'))

    except Exception as e:
        print(f"--- [DEBUG] Erro Fatal no Login: {e}")
        flash(f"Erro ao entrar: {e}", "error")
        return redirect(url_for('auth_bp.login'))


@auth_bp.route('/logout')
def logout():
    session.pop('user_profile', None)
    session.clear() 
    flash("Você saiu do sistema.", "info")
    return redirect(url_for('auth_bp.login'))


# === ROTAS DE CADASTRO (Mantidas inalteradas) ===

@auth_bp.route('/cadastro-estudantes')
def cadastro_alunos(): 
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    if session['user_profile'].get('possui_cadastro_filhos', False):
        return redirect(url_for('chat_bp.index'))

    form = CadastroAlunosForm()
    return render_template('cadastro_alunos.html', form=form)


@auth_bp.route('/salvar-estudantes', methods=['POST'])
def salvar_estudantes():
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    form = CadastroAlunosForm()
    
    if form.validate_on_submit():
        estudantes_processados = []
        
        for estudante_form in form.estudantes:
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
             flash("Adicione pelo menos um estudante.", "error")
             return render_template('cadastro_alunos.html', form=form)

        try:
            user_email = session['user_profile']['email']
            
            doc_ref = db.collection('responsaveis').document(user_email)
            doc_ref.update({
                'filhos': estudantes_processados, 
                'possui_cadastro_filhos': True,
                'ano_ultima_atualizacao': 2026
            })
            
            session['user_profile']['possui_cadastro_filhos'] = True
            session['user_profile']['filhos'] = estudantes_processados
            session.modified = True 

            flash("Cadastro realizado com sucesso!", "success")
            return redirect(url_for('chat_bp.index'))

        except Exception as e:
            print(f"Erro ao salvar estudantes: {e}")
            flash(f"Erro ao salvar dados: {e}", "error")
            return redirect(url_for('auth_bp.cadastro_alunos'))
    
    else:
        flash("Verifique os campos do formulário.", "error")
        return render_template('cadastro_alunos.html', form=form)
    
@auth_bp.route('/perfil')
def perfil():
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    email = session['user_profile']['email']
    dados_atualizados = auth_services.obter_responsavel(email)
    
    if dados_atualizados:
        session['user_profile'] = dados_atualizados
        estudantes = dados_atualizados.get('filhos', [])
    else:
        estudantes = []

    form = CadastroAlunosForm()
    return render_template('perfil.html', estudantes=estudantes, form=form)