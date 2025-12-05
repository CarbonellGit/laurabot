"""
Rotas do Módulo Admin

Gerencia upload e gestão de comunicados com segurança baseada em Roles
e logging estruturado para auditoria.
"""
import unicodedata
import re
from flask import render_template, session, redirect, url_for, flash, abort, request
from google.cloud import firestore

from . import admin_bp
from src.core import parser, storage, vector_db
from src.core.database import db 
from src.core.logger import get_logger

# Inicializa logger
logger = get_logger(__name__)

COLLECTION_COMUNICADOS = 'comunicados'

def verificar_admin():
    """
    Verifica se o usuário logado tem a role 'admin' no seu perfil de sessão.
    Isso substitui a verificação insegura por variáveis de ambiente.
    """
    user_profile = session.get('user_profile')
    if not user_profile: 
        return False
    
    # A role deve vir do banco de dados (carregada no login)
    # Se não tiver role definida, assume 'user' (False)
    es_admin = user_profile.get('role') == 'admin'
    
    if not es_admin:
        logger.warning(f"Acesso negado ao Admin: {user_profile.get('email')} tentou acessar.")
    
    return es_admin

def limpar_nome_para_id(texto):
    if not texto: return ""
    nfkd_form = unicodedata.normalize('NFKD', texto)
    texto_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    texto_limpo = re.sub(r'[^a-zA-Z0-9\.\-_]', '_', texto_ascii)
    return texto_limpo

@admin_bp.before_request
def restringir_acesso():
    if 'user_profile' not in session: return redirect(url_for('auth_bp.login'))
    if not verificar_admin(): abort(403)

@admin_bp.route('/')
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/gerenciar')
def gerenciar_arquivos():
    try:
        docs_ref = db.collection(COLLECTION_COMUNICADOS).order_by('criado_em', direction=firestore.Query.DESCENDING).stream()
        arquivos = []
        for doc in docs_ref:
            dados = doc.to_dict()
            dados['id'] = doc.id
            arquivos.append(dados)
        return render_template('admin/gerenciar.html', arquivos=arquivos)
    except Exception as e:
        logger.error("Erro ao listar arquivos no dashboard.", exc_info=True)
        flash(f"Erro ao listar arquivos: {e}", "error")
        return redirect(url_for('admin_bp.dashboard'))

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
    
    integral_check = request.form.get('integral')
    is_integral = True if integral_check == 'on' else False

    user_email = session['user_profile']['email']

    try:
        logger.info(f"Iniciando upload: {arquivo.filename} por {user_email}")
        
        url_publica = storage.upload_file(arquivo, arquivo.filename)
        arquivo.seek(0) 
        texto_extraido = parser.extrair_texto_pdf(arquivo)
        doc_id = limpar_nome_para_id(arquivo.filename)

        metadados = {
            'nome_arquivo': arquivo.filename,
            'url_download': url_publica,
            'segmento': segmento_form,
            'series': series_form,     
            'periodos': periodos_form, 
            'turmas': turmas_form,
            'integral': is_integral,
            'criado_por': user_email, # Auditoria
            'criado_em': firestore.SERVER_TIMESTAMP
        }

        db.collection(COLLECTION_COMUNICADOS).document(doc_id).set(metadados)
        logger.info(f"Metadados salvos no Firestore: {doc_id}")

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
        logger.critical(f"Falha no processo de upload do arquivo {arquivo.filename}: {e}", exc_info=True)
        flash(f"Erro ao processar: {e}", "error")
        return redirect(url_for('admin_bp.dashboard'))

@admin_bp.route('/excluir/<doc_id>', methods=['POST'])
def excluir_arquivo(doc_id):
    user_email = session['user_profile']['email']
    try:
        logger.info(f"Solicitação de exclusão: {doc_id} por {user_email}")

        doc_ref = db.collection(COLLECTION_COMUNICADOS).document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            logger.warning(f"Tentativa de excluir arquivo inexistente: {doc_id}")
            flash("Arquivo não encontrado no registro.", "error")
            return redirect(url_for('admin_bp.gerenciar_arquivos'))
        
        dados = doc.to_dict()
        url_download = dados.get('url_download')

        if url_download: storage.delete_file(url_download)
        vector_db.excluir_do_vetor(doc_id)
        doc_ref.delete()

        flash("Comunicado excluído permanentemente.", "success")
        return redirect(url_for('admin_bp.gerenciar_arquivos'))

    except Exception as e:
        logger.error(f"Erro ao excluir {doc_id}: {e}", exc_info=True)
        flash(f"Erro ao excluir: {e}", "error")
        return redirect(url_for('admin_bp.gerenciar_arquivos'))

@admin_bp.route('/editar/<doc_id>', methods=['GET', 'POST'])
def editar_arquivo(doc_id):
    try:
        doc_ref = db.collection(COLLECTION_COMUNICADOS).document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            abort(404)

        if request.method == 'POST':
            integral_check = request.form.get('integral')
            is_integral = True if integral_check == 'on' else False

            novos_dados = {
                'segmento': request.form.get('segmento'),
                'series': request.form.getlist('series'),
                'periodos': request.form.getlist('periodo'),
                'turmas': request.form.getlist('turma'),
                'integral': is_integral
            }
            
            doc_ref.update(novos_dados)
            vector_db.atualizar_metadados_vetor(doc_id, novos_dados)

            logger.info(f"Arquivo {doc_id} editado por {session['user_profile']['email']}")
            flash("Metadados atualizados com sucesso!", "success")
            return redirect(url_for('admin_bp.gerenciar_arquivos'))

        dados = doc.to_dict()
        return render_template('admin/editar.html', arquivo=dados, doc_id=doc_id)

    except Exception as e:
        logger.error(f"Erro na edição de {doc_id}: {e}", exc_info=True)
        flash(f"Erro ao editar: {e}", "error")
        return redirect(url_for('admin_bp.gerenciar_arquivos'))