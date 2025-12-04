"""
Rotas do Módulo Admin
"""
import os
from flask import render_template, session, redirect, url_for, flash, abort, request
from . import admin_bp

# Importa o nosso novo motor de leitura (Parser)
from src.core import parser

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
    Processa o upload do arquivo, extrai texto e metadados.
    """
    # 1. Verificações básicas
    if 'arquivo' not in request.files:
        return "Erro: Nenhum arquivo enviado.", 400
    
    arquivo = request.files['arquivo']
    
    if arquivo.filename == '':
        return "Erro: Nome de arquivo vazio.", 400

    # 2. Metadados do Form (O que o Admin selecionou manualmente)
    segmento_form = request.form.get('segmento')
    series_form = request.form.getlist('series')

    # 3. Processamento Inteligente (Parser)
    print(f"--- INICIANDO PROCESSAMENTO DO PDF: {arquivo.filename} ---")
    
    # Extração de Texto (OCR/Leitura)
    texto_extraido = parser.extrair_texto_pdf(arquivo)
    
    # Análise Automática (apenas para log por enquanto, RF-009)
    tags_auto = parser.analisar_nome_arquivo(arquivo.filename)

    print(f"1. Segmento Selecionado: {segmento_form}")
    print(f"2. Tags Detectadas no Nome: {tags_auto}")
    print(f"3. Tamanho do Texto Extraído: {len(texto_extraido)} caracteres")
    
    print("--- INÍCIO DO CONTEÚDO (Primeiros 500 caracteres) ---")
    print(texto_extraido[:500])
    print("--- FIM DA AMOSTRA ---")

    # AQUI ENTRARÁ O BANCO VETORIAL (Próxima etapa)

    return redirect(url_for('admin_bp.dashboard'))