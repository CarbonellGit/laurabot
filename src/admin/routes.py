"""
Rotas do Módulo Admin

Refatorado com PROCESSAMENTO ASSÍNCRONO (Threads), Segurança baseada em Roles,
Parser Inteligente (IA) e Logging Estruturado.
"""
import threading
import unicodedata
import re
from flask import (
    render_template, 
    session, 
    redirect, 
    url_for, 
    flash, 
    abort, 
    request, 
    current_app
)
from google.cloud import firestore

from . import admin_bp
from src.core import parser, storage, vector_db
from src.core.database import db 
from src.core.logger import get_logger

# Inicializa logger padronizado
logger = get_logger(__name__)

COLLECTION_COMUNICADOS = 'comunicados'

# === FUNÇÕES AUXILIARES ===

def verificar_admin():
    """
    Verifica se o usuário tem a role 'admin' no banco de dados (via sessão).
    """
    user_profile = session.get('user_profile')
    if not user_profile: return False
    
    es_admin = user_profile.get('role') == 'admin'
    
    if not es_admin:
        logger.warning(f"Acesso negado ao Admin: {user_profile.get('email')} tentou acessar.")
    
    return es_admin

def limpar_nome_para_id(texto):
    """
    Gera um ID seguro para o documento a partir do nome do arquivo.
    """
    if not texto: return ""
    nfkd_form = unicodedata.normalize('NFKD', texto)
    texto_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return re.sub(r'[^a-zA-Z0-9\.\-_]', '_', texto_ascii)

@admin_bp.before_request
def restringir_acesso():
    """Bloqueia acesso de não-admins a qualquer rota deste blueprint."""
    if 'user_profile' not in session: return redirect(url_for('auth_bp.login'))
    if not verificar_admin(): abort(403)

# === TAREFA EM BACKGROUND (WORKER) ===

def _tarefa_processamento_background(app, doc_id, url_download, nome_arquivo, dados_manuais):
    """
    Executa o trabalho pesado em segundo plano:
    1. Baixa o PDF
    2. OCR (Extração de texto)
    3. Análise de IA (Gemini)
    4. Vetorização (Pinecone)
    5. Atualização de status no Firestore
    """
    # Necessário pois a thread roda fora do contexto original da requisição
    with app.app_context():
        try:
            logger.info(f"[BG] Iniciando processamento profundo de {doc_id}...")
            
            # 1. Baixa o PDF do Storage para memória (BytesIO)
            arquivo_bytes = storage.download_bytes(url_download)
            
            # 2. Extrai Texto
            texto_extraido = parser.extrair_texto_pdf(arquivo_bytes)
            
            # 3. Inteligência Artificial (Extração de Metadados)
            metadados_ia = parser.analisar_metadados_ia(texto_extraido, nome_arquivo)
            
            # 4. Merge de Dados (Prioridade: Manual > IA)
            segmento = dados_manuais['segmento'] if dados_manuais['segmento'] else metadados_ia['segmento']
            series = dados_manuais['series'] if dados_manuais['series'] else metadados_ia['series']
            assunto = metadados_ia.get('assunto', 'Processado Automaticamente')
            
            # 5. Atualiza Firestore (Sucesso)
            doc_ref = db.collection(COLLECTION_COMUNICADOS).document(doc_id)
            doc_ref.update({
                'segmento': segmento,
                'series': series,
                'assunto': assunto,
                'status': 'concluido', # Indica ao frontend que acabou
                'processado_em': firestore.SERVER_TIMESTAMP
            })
            
            # 6. Salva no Banco Vetorial (Pinecone)
            metadados_vetor = {
                'nome_arquivo': nome_arquivo,
                'url_download': url_download,
                'segmento': segmento,
                'series': series,
                'periodos': dados_manuais['periodos'],
                'turmas': dados_manuais['turmas'],
                'integral': dados_manuais['integral'],
                'assunto': assunto
            }
            
            # Enriquece o texto vetorizado com o Assunto identificado pela IA
            texto_final = f"Assunto: {assunto}\n\n{texto_extraido}"
            
            vector_db.salvar_no_vetor(doc_id, texto_final, metadados_vetor)
            
            logger.info(f"[BG] Processamento concluído com sucesso para {doc_id}")

        except Exception as e:
            logger.error(f"[BG] Erro ao processar {doc_id}: {e}", exc_info=True)
            # Registra o erro no banco para o admin saber
            try:
                db.collection(COLLECTION_COMUNICADOS).document(doc_id).update({
                    'status': 'erro',
                    'erro_msg': str(e)
                })
            except:
                pass

# === ROTAS ===

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
        logger.error(f"Erro ao listar arquivos: {e}", exc_info=True)
        flash("Erro ao carregar lista de arquivos.", "error")
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

    user_email = session['user_profile']['email']

    try:
        # 1. Upload Rápido (Síncrono)
        # O upload para o Storage é rápido o suficiente para ser feito na thread principal
        url_publica = storage.upload_file(arquivo, arquivo.filename)
        doc_id = limpar_nome_para_id(arquivo.filename)

        # 2. Captura dados do Form (Inputs manuais opcionais)
        dados_manuais = {
            'segmento': request.form.get('segmento'),
            'series': request.form.getlist('series'),
            'periodos': request.form.getlist('periodo'),
            'turmas': request.form.getlist('turma'),
            'integral': True if request.form.get('integral') == 'on' else False
        }

        # 3. Cria registro "Placeholder" no Firestore
        # Status 'processando' permite que a UI mostre um loader ou aviso
        metadados_iniciais = {
            'nome_arquivo': arquivo.filename,
            'url_download': url_publica,
            'status': 'processando', 
            'criado_por': user_email,
            'criado_em': firestore.SERVER_TIMESTAMP,
            **dados_manuais
        }

        db.collection(COLLECTION_COMUNICADOS).document(doc_id).set(metadados_iniciais)

        # 4. Dispara Thread de Processamento (Fogo e Esquece)
        # Passamos o app real para que a thread tenha acesso às configs (API Keys)
        app_real = current_app._get_current_object()
        thread = threading.Thread(
            target=_tarefa_processamento_background,
            args=(app_real, doc_id, url_publica, arquivo.filename, dados_manuais)
        )
        thread.start()

        logger.info(f"Upload inicial aceito. Thread disparada para {doc_id}")
        flash(f"Arquivo '{arquivo.filename}' recebido! O processamento inteligente (IA) continua em segundo plano.", "success")
        return redirect(url_for('admin_bp.gerenciar_arquivos'))

    except Exception as e:
        logger.critical(f"Falha crítica no upload inicial: {e}", exc_info=True)
        flash(f"Erro ao iniciar upload: {e}", "error")
        return redirect(url_for('admin_bp.dashboard'))

@admin_bp.route('/excluir/<doc_id>', methods=['POST'])
def excluir_arquivo(doc_id):
    user_email = session['user_profile']['email']
    try:
        logger.info(f"Solicitação de exclusão: {doc_id} por {user_email}")

        doc_ref = db.collection(COLLECTION_COMUNICADOS).document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            flash("Arquivo não encontrado.", "error")
            return redirect(url_for('admin_bp.gerenciar_arquivos'))
        
        dados = doc.to_dict()
        url_download = dados.get('url_download')

        # Limpeza completa (Storage, Vector DB, Firestore)
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
            # Atualização de Metadados Manuais
            integral_check = request.form.get('integral')
            is_integral = True if integral_check == 'on' else False

            novos_dados = {
                'segmento': request.form.get('segmento'),
                'series': request.form.getlist('series'),
                'periodos': request.form.getlist('periodo'),
                'turmas': request.form.getlist('turma'),
                'integral': is_integral
            }
            
            # Atualiza no Firestore
            doc_ref.update(novos_dados)
            
            # Atualiza no Pinecone (para refletir na busca imediatamente)
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