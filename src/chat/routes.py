"""
Rotas do Módulo de Chat

Consolidado: Implementa RAG com Memória Persistente (Firestore) 
e Streaming de Resposta (Yield/Generator) para UX otimizada.
"""

from flask import (
    render_template, 
    session, 
    redirect, 
    url_for, 
    request, 
    jsonify, 
    Response, 
    stream_with_context
)
from google.cloud import firestore

from . import chat_bp
from src.core import vector_db 
from src.core.database import db
from src.core.logger import get_logger

logger = get_logger(__name__)

COLLECTION_HISTORY = 'chat_history'

# === FUNÇÕES AUXILIARES DE PERSISTÊNCIA ===

def _salvar_mensagem(user_email: str, role: str, content: str):
    """
    Salva uma mensagem individual no Firestore para auditoria e histórico futuro.
    """
    try:
        mensagem = {
            'user_email': user_email,
            'role': role,
            'content': content,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        db.collection(COLLECTION_HISTORY).add(mensagem)
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem no DB: {e}", exc_info=True)

def _carregar_historico(user_email: str, limite=10) -> list:
    """
    Recupera as últimas N mensagens do usuário para contexto imediato.
    Retorna em ordem cronológica (antigas -> novas).
    """
    try:
        # Busca as mais recentes (DESC)
        docs = (
            db.collection(COLLECTION_HISTORY)
            .where('user_email', '==', user_email)
            .order_by('timestamp', direction=firestore.Query.DESCENDING)
            .limit(limite)
            .stream()
        )
        
        historico = []
        for doc in docs:
            dados = doc.to_dict()
            historico.append({
                'role': dados.get('role'),
                'content': dados.get('content')
            })
            
        # Inverte para ficar na ordem correta (Cronológica) para o Chat/LLM
        return historico[::-1]

    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {e}", exc_info=True)
        return []

# === ROTAS ===

@chat_bp.route('/')
def index():
    """
    Carrega a interface do chat e o histórico persistente do usuário.
    """
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    user_profile = session['user_profile']
    user_email = user_profile['email']
    
    if not user_profile.get('possui_cadastro_filhos', False):
         return redirect(url_for('auth_bp.cadastro_alunos'))

    # Carrega as últimas 20 mensagens para exibir na tela
    historico_mensagens = _carregar_historico(user_email, limite=20)

    # Saudação apenas se for um chat "vazio" (sem histórico recente)
    mensagem_inicial = None
    if not historico_mensagens:
        nome_usuario = user_profile.get('nome', 'Responsável').split()[0]
        mensagem_inicial = f"Olá, {nome_usuario}! Como posso ajudar com os comunicados escolares hoje?"

    return render_template('chat.html', 
                           historico=historico_mensagens, 
                           mensagem_inicial=mensagem_inicial)


@chat_bp.route('/enviar', methods=['POST'])
def enviar_mensagem():
    """
    Processa a mensagem do usuário via Streaming.
    1. Salva a pergunta.
    2. Busca contexto (RAG).
    3. Gera resposta pedaço por pedaço (yield).
    4. Salva a resposta completa ao final.
    """
    if 'user_profile' not in session:
        # Retorna 401 para que o JS possa redirecionar ou avisar
        return jsonify({'error': 'Sessão expirada. Faça login novamente.'}), 401

    data = request.get_json()
    mensagem_usuario = data.get('message', '').strip()

    if not mensagem_usuario:
        return jsonify({'error': 'Mensagem vazia.'}), 400

    user_profile = session['user_profile']
    user_email = user_profile['email']
    filhos = user_profile.get('filhos', [])
    
    logger.info(f"Mensagem de {user_email}: {mensagem_usuario[:30]}...")

    # 1. Salva a pergunta do usuário no Banco
    _salvar_mensagem(user_email, 'user', mensagem_usuario)

    # 2. Identificação de Contexto (Segmento)
    # Lógica simples baseada em nome do filho (será aprimorada com IA futuramente)
    segmentos_busca = list(set([f['segmento'] for f in filhos]))
    mensagem_lower = mensagem_usuario.lower()
    
    for filho in filhos:
        primeiro_nome = filho['nome'].split()[0].lower()
        if primeiro_nome in mensagem_lower:
            segmentos_busca = [filho['segmento']]
            break 
            
    try:
        # 3. Prepara o terreno para a IA
        # Histórico curto para contexto da LLM (últimas 6 mensagens / 3 turnos)
        historico_contexto = _carregar_historico(user_email, limite=6)

        # Busca Vetorial (RAG)
        documentos_relevantes = vector_db.buscar_documentos(
            query=mensagem_usuario,
            filtro_segmentos=segmentos_busca,
            top_k=3 
        )

        # Função Geradora Interna (Clousure para capturar variáveis locais)
        def gerar_stream():
            resposta_completa = ""
            
            # Itera sobre os pedaços gerados pelo Gemini
            # vector_db.gerar_resposta_ia_stream deve ser um generator (com yield)
            for chunk in vector_db.gerar_resposta_ia_stream(
                pergunta=mensagem_usuario,
                contextos=documentos_relevantes,
                historico=historico_contexto,
                perfil_usuario=user_profile
            ):
                # Acumula o texto para salvar no banco depois
                resposta_completa += chunk
                
                # Envia o pedaço imediatamente para o navegador
                yield chunk

            # Fim do stream: Salva a resposta completa no Banco de Dados
            # Isso garante que o histórico fique íntegro
            _salvar_mensagem(user_email, 'assistant', resposta_completa)
        
        # Retorna o objeto Response configurado para streaming
        return Response(stream_with_context(gerar_stream()), mimetype='text/plain')

    except Exception as e:
        logger.error(f"Erro no fluxo do Chat: {e}", exc_info=True)
        # Em caso de erro no início, tenta retornar um JSON de erro
        # Se o stream já começou, o erro vai quebrar o chunk no cliente (tratado no JS)
        return jsonify({'error': 'Erro interno no servidor.'}), 500