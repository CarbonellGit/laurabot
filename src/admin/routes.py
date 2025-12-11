"""
Rotas do Módulo Admin

Refatorado: Passagem segura de parâmetros para Thread (Blob Name).
"""
import threading
import unicodedata
import re
import traceback # Para imprimir erro detalhado no terminal
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

logger = get_logger(__name__)
COLLECTION_COMUNICADOS = 'comunicados'

# === FUNÇÕES AUXILIARES ===

def verificar_admin():
    user_profile = session.get('user_profile')
    if not user_profile: return False
    es_admin = user_profile.get('role') == 'admin'
    if not es_admin:
        logger.warning(f"Acesso negado: {user_profile.get('email')}")
    return es_admin

def limpar_nome_para_id(texto):
    if not texto: return ""
    nfkd_form = unicodedata.normalize('NFKD', texto)
    texto_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return re.sub(r'[^a-zA-Z0-9\.\-_]', '_', texto_ascii)

@admin_bp.before_request
def restringir_acesso():
    if 'user_profile' not in session: return redirect(url_for('auth_bp.login'))
    if not verificar_admin(): abort(403)

# === TAREFA EM BACKGROUND (WORKER) ===

def _tarefa_processamento_background(app, doc_id, nome_blob, url_download, nome_arquivo, dados_manuais):
    """
    Executa o processamento pesado.
    Usa 'nome_blob' para download seguro.
    """
    print(f"🚀 [THREAD] Iniciando processamento para: {doc_id}") # Debug Visual
    
    with app.app_context():
        try:
            # 1. Baixa o PDF usando o NOME SEGURO
            print(f"📥 [THREAD] Baixando blob: {nome_blob}...")
            arquivo_bytes = storage.download_bytes_by_name(nome_blob)
            
            # 2. Extrai Texto
            print("📄 [THREAD] Extraindo texto...")
            texto_extraido = parser.extrair_texto_pdf(arquivo_bytes)
            if not texto_extraido:
                raise ValueError("OCR retornou texto vazio ou PDF ilegível.")

            # 3. Inteligência Artificial
            print("🤖 [THREAD] Consultando Gemini...")
            metadados_ia = parser.analisar_metadados_ia(texto_extraido, nome_arquivo)
            
            # 4. Merge de Dados
            segmento = dados_manuais['segmento'] if dados_manuais['segmento'] else metadados_ia['segmento']
            series = dados_manuais['series'] if dados_manuais['series'] else metadados_ia['series']
            
            turmas_ia = metadados_ia.get('turmas', [])
            turmas = dados_manuais['turmas'] if dados_manuais['turmas'] else turmas_ia
            
            assunto = metadados_ia.get('assunto', 'Processado Automaticamente')
            
            # 5. Atualiza Firestore
            print("💾 [THREAD] Salvando no Firestore...")
            doc_ref = db.collection(COLLECTION_COMUNICADOS).document(doc_id)
            doc_ref.update({
                'segmento': segmento,
                'series': series,
                'turmas': turmas,
                'assunto': assunto,
                'status': 'concluido',
                'processado_em': firestore.SERVER_TIMESTAMP
            })
            
            # 6. Salva no Vetor
            print("🧠 [THREAD] Salvando no Pinecone...")
            metadados_vetor = {
                'nome_arquivo': nome_arquivo,
                'url_download': url_download,
                'segmento': segmento,
                'series': series,
                'periodos': dados_manuais['periodos'],
                'turmas': turmas,
                'integral': dados_manuais['integral'],
                'assunto': assunto
            }
            
            series_str = ", ".join(series) if series else "Todas"
            turmas_str = ", ".join(turmas) if turmas else "Todas"
            
            texto_final = (
                f"Metadados Importantes:\n"
                f"Assunto: {assunto}\n"
                f"Segmento: {segmento}\n"
                f"Séries: {series_str}\n"
                f"Turmas: {turmas_str}\n"
                f"----------------\n"
                f"{texto_extraido}"
            )
            
            vector_db.salvar_no_vetor(doc_id, texto_final, metadados_vetor)
            
            print(f"✅ [THREAD] SUCESSO TOTAL: {doc_id}")
            logger.info(f"[BG] Sucesso total no arquivo {doc_id}")

        except Exception as e:
            err_msg = str(e)
            print(f"❌ [THREAD] ERRO FATAL: {err_msg}")
            traceback.print_exc() # Imprime erro completo no terminal
            logger.error(f"[BG] Erro ao processar {doc_id}: {e}", exc_info=True)
            
            # Tenta atualizar o status para erro no Firestore
            try:
                if db:
                    db.collection(COLLECTION_COMUNICADOS).document(doc_id).update({
                        'status': 'erro',
                        'erro_msg': f"Falha no processamento: {err_msg}"
                    })
            except Exception as db_err:
                 logger.critical(f"Falha ao salvar status de erro no DB: {db_err}")

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
        logger.error(f"Erro dashboard: {e}", exc_info=True)
        return redirect(url_for('admin_bp.dashboard'))

@admin_bp.route('/status/<doc_id>')
def check_status(doc_id):
    """
    Endpoint para Polling (Frontend verifica se terminou de processar).
    Retorna JSON: { "status": "processando" | "concluido" | "erro" }
    """
    try:
        doc_ref = db.collection(COLLECTION_COMUNICADOS).document(doc_id)
        doc = doc_ref.get()
        if not doc.exists:
            return {"status": "erro", "msg": "Não encontrado"}, 404
        
        dados = doc.to_dict()
        return {
            "status": dados.get('status', 'processando'),
            "msg": dados.get('erro_msg', '')
        }
    except Exception as e:
        return {"status": "erro", "msg": str(e)}, 500

@admin_bp.route('/upload')
def upload_form():
    return render_template('admin/upload.html')

@admin_bp.route('/upload-arquivo', methods=['POST'])
def upload_arquivo():
    if 'arquivo' not in request.files:
        flash("Nenhum arquivo.", "error")
        return redirect(url_for('admin_bp.upload_form'))
    
    arquivo = request.files['arquivo']
    if arquivo.filename == '':
        flash("Nome vazio.", "error")
        return redirect(url_for('admin_bp.upload_form'))

    # Validação do Arquivo (Filtro por Extensão)
    if not arquivo.filename.lower().endswith('.pdf'):
        flash("Apenas arquivos PDF são permitidos.", "error")
        return redirect(url_for('admin_bp.upload_form'))

    # Validação de Magic Numbers (Segurança)
    try:
        header = arquivo.read(4)
        arquivo.seek(0) # IMPORTANTÍSSIMO: Resetar o ponteiro!
        if header != b'%PDF':
            flash("Arquivo inválido (Conteúdo não é PDF).", "error")
            logger.warning(f"Upload rejeitado (Magic Number inválido): {arquivo.filename} por {user_email}")
            return redirect(url_for('admin_bp.upload_form'))
    except Exception as e:
        logger.error(f"Erro ao ler header do arquivo: {e}")
        flash("Erro ao validar arquivo.", "error")
        return redirect(url_for('admin_bp.upload_form'))

    user_email = session['user_profile']['email']

    try:
        # 1. Upload Rápido (Retorna URL e NOME DO BLOB)
        url_publica, nome_blob = storage.upload_file(arquivo, arquivo.filename)
        doc_id = limpar_nome_para_id(arquivo.filename)
        
        # 2. Dados Manuais
        dados_manuais = {
            'segmento': request.form.get('segmento'),
            'series': request.form.getlist('series'),
            'periodos': request.form.getlist('periodo'),
            'turmas': request.form.getlist('turma'),
            'integral': True if request.form.get('integral') == 'on' else False
        }

        # 3. Placeholder no Firestore
        metadados_iniciais = {
            'nome_arquivo': arquivo.filename,
            'url_download': url_publica,
            'status': 'processando', 
            'criado_por': user_email,
            'criado_em': firestore.SERVER_TIMESTAMP,
            **dados_manuais
        }
        
        db.collection(COLLECTION_COMUNICADOS).document(doc_id).set(metadados_iniciais)
        
        # 4. Dispara Thread com NOME DO BLOB
        app_real = current_app._get_current_object()
        thread = threading.Thread(
            target=_tarefa_processamento_background,
            # Passamos nome_blob aqui v
            args=(app_real, doc_id, nome_blob, url_publica, arquivo.filename, dados_manuais)
        )
        thread.start()

        logger.info(f"Upload iniciado: {doc_id}")
        flash(f"Upload iniciado! Processando em segundo plano.", "success")
        return redirect(url_for('admin_bp.gerenciar_arquivos'))

    except Exception as e:
        logger.critical(f"Erro no início do upload: {e}", exc_info=True)
        flash(f"Erro ao iniciar: {e}", "error")
        return redirect(url_for('admin_bp.dashboard'))

@admin_bp.route('/excluir/<doc_id>', methods=['POST'])
def excluir_arquivo(doc_id):
    # (Mantém igual)
    try:
        doc_ref = db.collection(COLLECTION_COMUNICADOS).document(doc_id)
        doc = doc_ref.get()
        if doc.exists:
            dados = doc.to_dict()
            if dados.get('url_download'): storage.delete_file(dados['url_download'])
            vector_db.excluir_do_vetor(doc_id)
            doc_ref.delete()
            flash("Excluído com sucesso.", "success")
    except Exception as e:
        logger.error(f"Erro excluir: {e}")
    return redirect(url_for('admin_bp.gerenciar_arquivos'))

@admin_bp.route('/editar/<doc_id>', methods=['GET', 'POST'])
def editar_arquivo(doc_id):
    # (Mantém igual - use o código completo das fases anteriores)
    doc_ref = db.collection(COLLECTION_COMUNICADOS).document(doc_id)
    doc = doc_ref.get()
    if not doc.exists: abort(404)
    
    if request.method == 'POST':
        try:
            novos = {
                'segmento': request.form.get('segmento'),
                'series': request.form.getlist('series'),
                'periodos': request.form.getlist('periodo'),
                'turmas': request.form.getlist('turma'),
                'integral': True if request.form.get('integral') == 'on' else False
            }
            doc_ref.update(novos)
            vector_db.atualizar_metadados_vetor(doc_id, novos)
            flash("Atualizado.", "success")
            return redirect(url_for('admin_bp.gerenciar_arquivos'))
        except Exception as e:
            flash(f"Erro: {e}", "error")

    return render_template('admin/editar.html', arquivo=doc.to_dict(), doc_id=doc_id)