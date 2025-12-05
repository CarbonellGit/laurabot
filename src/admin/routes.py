"""
Rotas do Módulo Admin
Gerencia Upload, Listagem, Edição e Exclusão de Comunicados.
"""
import os
import unicodedata
import re
from flask import render_template, session, redirect, url_for, flash, abort, request
from google.cloud import firestore

from . import admin_bp

# Importa os serviços do Core
from src.core import parser, storage, vector_db
from src.core.database import db # Importa a conexão com Firestore

COLLECTION_COMUNICADOS = 'comunicados'

def verificar_admin():
    """Verifica se o usuário logado está na lista de e-mails de admin."""
    user_profile = session.get('user_profile')
    if not user_profile: return False
    admins_env = os.environ.get('ADMIN_EMAILS', '')
    lista_admins = [e.strip() for e in admins_env.split(',')]
    return session['user_profile']['email'] in lista_admins

def limpar_nome_para_id(texto):
    """
    Remove acentos e caracteres especiais para satisfazer o requisito ASCII do Pinecone.
    """
    if not texto: return ""
    nfkd_form = unicodedata.normalize('NFKD', texto)
    texto_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    texto_limpo = re.sub(r'[^a-zA-Z0-9\.\-_]', '_', texto_ascii)
    return texto_limpo

@admin_bp.before_request
def restringir_acesso():
    """Bloqueia todas as rotas /admin para não-admins."""
    if 'user_profile' not in session: return redirect(url_for('auth_bp.login'))
    if not verificar_admin(): abort(403)

# === DASHBOARD & LISTAGEM ===

@admin_bp.route('/')
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/gerenciar')
def gerenciar_arquivos():
    """
    Lista todos os comunicados cadastrados no Firestore.
    """
    try:
        # Busca todos os documentos da coleção, ordenados por data (decrescente)
        docs_ref = db.collection(COLLECTION_COMUNICADOS).order_by('criado_em', direction=firestore.Query.DESCENDING).stream()
        
        arquivos = []
        for doc in docs_ref:
            dados = doc.to_dict()
            dados['id'] = doc.id # Importante para os links de editar/excluir
            arquivos.append(dados)
            
        return render_template('admin/gerenciar.html', arquivos=arquivos)
    except Exception as e:
        flash(f"Erro ao listar arquivos: {e}", "error")
        return redirect(url_for('admin_bp.dashboard'))

# === UPLOAD (CRIAÇÃO) ===

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
        
        # 2. Extração de Texto
        arquivo.seek(0) 
        texto_extraido = parser.extrair_texto_pdf(arquivo)
        
        # 3. ID Seguro
        doc_id = limpar_nome_para_id(arquivo.filename)

        # 4. Dados para Salvar
        metadados = {
            'nome_arquivo': arquivo.filename,
            'url_download': url_publica,
            'segmento': segmento_form,
            'series': series_form,     
            'periodos': periodos_form, 
            'turmas': turmas_form,
            'criado_em': firestore.SERVER_TIMESTAMP
        }

        # 5. Salva no Firestore (Catálogo)
        db.collection(COLLECTION_COMUNICADOS).document(doc_id).set(metadados)

        # 6. Salva no Vector DB (Inteligência)
        # Removemos o timestamp para o Pinecone pois ele não suporta o objeto nativo do Firestore
        metadados_pinecone = metadados.copy()
        if 'criado_em' in metadados_pinecone: del metadados_pinecone['criado_em']

        vector_db.salvar_no_vetor(
            doc_id=doc_id,
            texto_completo=texto_extraido,
            metadados=metadados_pinecone
        )
        
        flash(f"Upload concluído com sucesso!", "success")
        return redirect(url_for('admin_bp.gerenciar_arquivos'))

    except Exception as e:
        print(f"ERRO CRÍTICO NO UPLOAD: {e}")
        flash(f"Erro ao processar: {e}", "error")
        return redirect(url_for('admin_bp.dashboard'))

# === EXCLUSÃO ===

@admin_bp.route('/excluir/<doc_id>', methods=['POST'])
def excluir_arquivo(doc_id):
    """
    Remove o arquivo de todas as camadas: Firestore, Storage e Pinecone.
    """
    try:
        # 1. Busca dados no Firestore para pegar a URL do arquivo
        doc_ref = db.collection(COLLECTION_COMUNICADOS).document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            flash("Arquivo não encontrado no registro.", "error")
            return redirect(url_for('admin_bp.gerenciar_arquivos'))
        
        dados = doc.to_dict()
        url_download = dados.get('url_download')

        # 2. Remove do Storage (Google Cloud)
        if url_download:
            storage.delete_file(url_download)

        # 3. Remove do Pinecone (Vector DB)
        vector_db.excluir_do_vetor(doc_id)

        # 4. Remove do Firestore (Catálogo)
        doc_ref.delete()

        flash("Comunicado excluído permanentemente.", "success")
        return redirect(url_for('admin_bp.gerenciar_arquivos'))

    except Exception as e:
        flash(f"Erro ao excluir: {e}", "error")
        return redirect(url_for('admin_bp.gerenciar_arquivos'))

# === EDIÇÃO (METADADOS) ===

@admin_bp.route('/editar/<doc_id>', methods=['GET', 'POST'])
def editar_arquivo(doc_id):
    """
    Permite alterar o público-alvo (Segmento, Série, etc.) de um arquivo já enviado.
    """
    doc_ref = db.collection(COLLECTION_COMUNICADOS).document(doc_id)
    doc = doc_ref.get()

    if not doc.exists:
        abort(404)

    # Se for POST, salva as alterações
    if request.method == 'POST':
        try:
            novos_dados = {
                'segmento': request.form.get('segmento'),
                'series': request.form.getlist('series'),
                'periodos': request.form.getlist('periodo'),
                'turmas': request.form.getlist('turma')
            }
            
            # Atualiza Firestore
            doc_ref.update(novos_dados)
            
            # Atualiza Pinecone (Metadata Update)
            # Precisamos garantir que os campos extras do Pinecone (url, nome) sejam preservados ou passados se necessário.
            # O método update do Pinecone faz merge se usarmos set_metadata.
            vector_db.atualizar_metadados_vetor(doc_id, novos_dados)

            flash("Metadados atualizados com sucesso!", "success")
            return redirect(url_for('admin_bp.gerenciar_arquivos'))
            
        except Exception as e:
            flash(f"Erro ao atualizar: {e}", "error")

    # Se for GET, exibe o form preenchido
    dados = doc.to_dict()
    return render_template('admin/editar.html', arquivo=dados, doc_id=doc_id)