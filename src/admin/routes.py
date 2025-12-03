"""
Rotas do Módulo Admin
"""
import os
# ADICIONADO: 'request' na lista de imports
from flask import render_template, session, redirect, url_for, flash, abort, request
from . import admin_bp

def verificar_admin():
    """
    Verifica se o usuário logado é um administrador.
    Lê a lista de e-mails do .env.
    """
    user_profile = session.get('user_profile')
    if not user_profile:
        return False
    
    email_usuario = user_profile.get('email')
    
    # Pega a lista do .env e limpa espaços extras
    admins_env = os.environ.get('ADMIN_EMAILS', '')
    lista_admins = [e.strip() for e in admins_env.split(',')]
    
    return email_usuario in lista_admins

@admin_bp.before_request
def restringir_acesso():
    """
    Executado antes de QUALQUER rota deste Blueprint.
    Bloqueia o acesso se não for admin.
    """
    # Se não estiver logado, manda pro login
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))
    
    # Se logado mas não for admin, lança erro 403 (Proibido)
    if not verificar_admin():
        abort(403, description="Acesso Negado: Você não tem permissão de administrador.")

@admin_bp.route('/')
def dashboard():
    """
    Painel Principal do Admin.
    """
    return render_template('admin/dashboard.html')

@admin_bp.route('/upload')
def upload_form():
    """
    Exibe o formulário de upload (HTML).
    """
    return render_template('admin/upload.html')

@admin_bp.route('/upload-arquivo', methods=['POST'])
def upload_arquivo():
    """
    Processa o upload do arquivo e os metadados.
    """
    # 1. Verifica se tem arquivo na requisição
    if 'arquivo' not in request.files:
        return "Erro: Nenhum arquivo enviado na requisição.", 400
    
    arquivo = request.files['arquivo']
    
    if arquivo.filename == '':
        return "Erro: Nenhum arquivo selecionado.", 400

    # 2. Pega os metadados do formulário
    segmento = request.form.get('segmento')
    series = request.form.getlist('series') # getlist pega múltiplos checkboxes selecionados

    print(f"--- UPLOAD RECEBIDO ---")
    print(f"Arquivo: {arquivo.filename}")
    print(f"Tipo: {arquivo.content_type}")
    print(f"Segmento: {segmento}")
    print(f"Séries: {series}")
    print(f"-----------------------")

    # AQUI ENTRARÁ O CÓDIGO DE PROCESSAMENTO DE PDF (Próxima etapa)

    # Redireciona de volta para o dashboard
    return redirect(url_for('admin_bp.dashboard'))