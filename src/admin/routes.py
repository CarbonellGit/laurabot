"""
Rotas do Módulo Admin
"""
import os
import unicodedata # <--- IMPORTANTE: Adicione este import
import re
from flask import render_template, session, redirect, url_for, flash, abort, request
from . import admin_bp

# Importa os serviços do Core
from src.core import parser, storage, vector_db

def verificar_admin():
    # ... (mesmo código de antes) ...
    user_profile = session.get('user_profile')
    if not user_profile: return False
    admins_env = os.environ.get('ADMIN_EMAILS', '')
    lista_admins = [e.strip() for e in admins_env.split(',')]
    return session['user_profile']['email'] in lista_admins

def limpar_nome_para_id(texto):
    """
    Remove acentos e caracteres especiais para satisfazer o requisito ASCII do Pinecone.
    Ex: 'Reunião 2º' -> 'Reuniao_2o'
    """
    if not texto: return ""
    
    # 1. Normaliza Unicode (separa o acento da letra: 'ã' vira 'a' + '~')
    nfkd_form = unicodedata.normalize('NFKD', texto)
    
    # 2. Filtra apenas os caracteres não-acento e codifica para ASCII
    texto_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    
    # 3. Substitui espaços e símbolos estranhos por underline
    # Mantém apenas letras, números, ponto, traço e underline
    texto_limpo = re.sub(r'[^a-zA-Z0-9\.\-_]', '_', texto_ascii)
    
    return texto_limpo

@admin_bp.before_request
def restringir_acesso():
    # ... (mesmo código de antes) ...
    if 'user_profile' not in session: return redirect(url_for('auth_bp.login'))
    if not verificar_admin(): abort(403)

@admin_bp.route('/')
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/upload')
def upload_form():
    return render_template('admin/upload.html')

@admin_bp.route('/upload-arquivo', methods=['POST'])
def upload_arquivo():
    if 'arquivo' not in request.files:
        flash("Erro: Nenhum arquivo enviado.", "error")
        return redirect(url_for('admin_bp.upload_form'))
    
    arquivo = request.files['arquivo']
    
    if arquivo.filename == '':
        flash("Erro: Nome de arquivo vazio.", "error")
        return redirect(url_for('admin_bp.upload_form'))

    # Metadados do Form
    segmento_form = request.form.get('segmento')
    series_form = request.form.getlist('series')
    periodos_form = request.form.getlist('periodo')
    turmas_form = request.form.getlist('turma')

    try:
        print(f"--- INICIANDO PROCESSAMENTO: {arquivo.filename} ---")
        
        # 1. Upload Storage (Gera Link)
        url_publica = storage.upload_file(arquivo, arquivo.filename)
        print(f"✅ Arquivo salvo na nuvem: {url_publica}")

        # 2. Extração de Texto
        arquivo.seek(0) 
        texto_extraido = parser.extrair_texto_pdf(arquivo)
        
        # 3. Tags (Apenas log)
        tags_auto = parser.analisar_nome_arquivo(arquivo.filename)
        
        print(f"✅ Texto extraído: {len(texto_extraido)} caracteres")

        # === IA (EMBEDDINGS) ===
        print("--- Gerando Inteligência (Embeddings) ---")
        
        metadados_ia = {
            'nome_arquivo': arquivo.filename, # Aqui mantemos o nome original com acento para exibição
            'url_download': url_publica,
            'segmento': segmento_form,
            'series': series_form,     
            'periodos': periodos_form, 
            'turmas': turmas_form      
        }

        # Gera ID seguro (ASCII) para o Pinecone
        doc_id = limpar_nome_para_id(arquivo.filename)

        vector_db.salvar_no_vetor(
            doc_id=doc_id,
            texto_completo=texto_extraido,
            metadados=metadados_ia
        )
        
        flash(f"Upload e Processamento de IA concluídos!", "success")
        return redirect(url_for('admin_bp.dashboard'))

    except Exception as e:
        print(f"ERRO CRÍTICO NO UPLOAD: {e}")
        # Mostra o erro na tela para facilitar
        flash(f"Erro ao processar: {e}", "error")
        return redirect(url_for('admin_bp.dashboard'))