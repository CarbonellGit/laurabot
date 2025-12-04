"""
Rotas do Módulo Admin
"""
import os
from flask import render_template, session, redirect, url_for, flash, abort, request
from . import admin_bp

# Importa os serviços do Core
from src.core import parser, storage

def verificar_admin():
    """
    Verifica se o usuário logado é um administrador.
    Lê a lista de e-mails do .env (ADMIN_EMAILS).
    """
    user_profile = session.get('user_profile')
    if not user_profile:
        return False
    
    email_usuario = user_profile.get('email')
    
    # Pega a lista do .env, separa por vírgula e limpa espaços
    admins_env = os.environ.get('ADMIN_EMAILS', '')
    lista_admins = [e.strip() for e in admins_env.split(',')]
    
    return email_usuario in lista_admins

@admin_bp.before_request
def restringir_acesso():
    """
    Middleware: Executado antes de QUALQUER rota deste Blueprint.
    Bloqueia o acesso se não for admin.
    """
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))
    
    if not verificar_admin():
        abort(403, description="Acesso Negado: Você não tem permissão de administrador.")

@admin_bp.route('/')
def dashboard():
    """Painel Principal."""
    return render_template('admin/dashboard.html')

@admin_bp.route('/upload')
def upload_form():
    """Exibe o formulário de upload."""
    return render_template('admin/upload.html')

@admin_bp.route('/upload-arquivo', methods=['POST'])
def upload_arquivo():
    """
    Processa o upload do arquivo:
    1. Salva no Google Cloud Storage (Link Público).
    2. Extrai texto e metadados.
    3. (Futuro) Gera Embeddings e salva no Pinecone.
    """
    # 1. Validações básicas de arquivo
    if 'arquivo' not in request.files:
        flash("Erro: Nenhum arquivo enviado.", "error")
        return redirect(url_for('admin_bp.upload_form'))
    
    arquivo = request.files['arquivo']
    
    if arquivo.filename == '':
        flash("Erro: Nome de arquivo vazio.", "error")
        return redirect(url_for('admin_bp.upload_form'))

    # 2. Captura Metadados do Formulário
    # get = valor único, getlist = múltiplos valores (checkboxes)
    segmento_form = request.form.get('segmento')
    series_form = request.form.getlist('series')
    periodos_form = request.form.getlist('periodo') # Filtro Manhã/Tarde
    turmas_form = request.form.getlist('turma')     # Filtro A, B, C...

    try:
        print(f"--- INICIANDO PROCESSAMENTO: {arquivo.filename} ---")
        print(f"Metadados Manuais: Seg={segmento_form}, Séries={series_form}, Períodos={periodos_form}, Turmas={turmas_form}")
        
        # 3. Upload para Google Cloud Storage (RF-008)
        # Gera o link HTTPS público para download
        url_publica = storage.upload_file(arquivo, arquivo.filename)
        print(f"✅ Arquivo salvo na nuvem: {url_publica}")

        # 4. Extração de Texto (RF-010)
        # Reseta o ponteiro do arquivo para o início, pois o upload o leu até o final
        arquivo.seek(0) 
        texto_extraido = parser.extrair_texto_pdf(arquivo)
        
        # Análise Automática de Nome (RF-009)
        tags_auto = parser.analisar_nome_arquivo(arquivo.filename)
        
        print(f"✅ Texto extraído: {len(texto_extraido)} caracteres")
        print(f"✅ Tags Automáticas: {tags_auto}")

        # Feedback de Sucesso
        flash(f"Upload concluído com sucesso! Link gerado.", "success")
        
        # (Opcional) Debug: Mostrar link na tela
        # flash(f"Link: {url_publica}", "info")

        return redirect(url_for('admin_bp.dashboard'))

    except Exception as e:
        print(f"ERRO CRÍTICO NO UPLOAD: {e}")
        flash(f"Erro ao processar arquivo: {str(e)}", "error")
        return redirect(url_for('admin_bp.dashboard'))