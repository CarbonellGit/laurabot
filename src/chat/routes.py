"""
Rotas do Módulo de Chat

Atualizado: 
- Correção de persistência de sessão (Conversation ID).
- Query Expansion para RAG.
"""

import uuid  # <--- IMPORTAÇÃO NOVA
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

def _salvar_mensagem(user_email: str, role: str, content: str, conversation_id: str):
    """
    Salva a mensagem no Firestore vinculada a um ID de conversa específico.
    """
    try:
        db.collection(COLLECTION_HISTORY).add({
            'user_email': user_email,
            'conversation_id': conversation_id, # <--- CAMPO NOVO
            'role': role,
            'content': content,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem no DB: {e}", exc_info=True)

def _carregar_historico(user_email: str, conversation_id: str, limite=20) -> list:
    """
    Carrega apenas as mensagens da conversa ATUAL.
    """
    try:
        # Filtra por email E pelo ID da conversa atual
        docs = (
            db.collection(COLLECTION_HISTORY)
            .where('user_email', '==', user_email)
            .where('conversation_id', '==', conversation_id) # <--- FILTRO NOVO
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
        return historico[::-1]
    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {e}", exc_info=True)
        return []

@chat_bp.route('/')
def index():
    if 'user_profile' not in session: return redirect(url_for('auth_bp.login'))
    user_profile = session['user_profile']
    
    # === SOLUÇÃO PROBLEMA 1 e 2 ===
    # Gera um novo ID de conversa a cada carregamento da página (F5 ou nova aba)
    # Isso garante que o chat comece "limpo" visualmente.
    conversation_id = str(uuid.uuid4())
    session['conversation_id'] = conversation_id
    
    # Como o ID é novo, isso retornará vazio, forçando a mensagem inicial
    historico = _carregar_historico(user_profile['email'], conversation_id)
    
    mensagem_inicial = None
    if not historico:
        nome = user_profile.get('nome', '').split()[0]
        mensagem_inicial = f"Olá, {nome}! Sou a LauraBot. Como posso ajudar com os comunicados escolares hoje?"
        
        # Opcional: Salvar a mensagem inicial no banco para ficar registrada na conversa
        # _salvar_mensagem(user_profile['email'], 'assistant', mensagem_inicial, conversation_id)

    return render_template('chat.html', historico=historico, mensagem_inicial=mensagem_inicial)


@chat_bp.route('/enviar', methods=['POST'])
def enviar_mensagem():
    if 'user_profile' not in session:
        return jsonify({'error': 'Sessão expirada.'}), 401

    # Recupera o ID da conversa atual da sessão
    conversation_id = session.get('conversation_id')
    if not conversation_id:
        # Fallback de segurança se a sessão tiver reiniciado
        conversation_id = str(uuid.uuid4())
        session['conversation_id'] = conversation_id

    data = request.get_json()
    mensagem_usuario = data.get('message', '').strip()
    if not mensagem_usuario: return jsonify({'error': 'Vazio'}), 400

    user_profile = session['user_profile']
    user_email = user_profile['email']
    filhos = user_profile.get('filhos', []) 
    
    # 1. Salva pergunta original com o ID da conversa
    _salvar_mensagem(user_email, 'user', mensagem_usuario, conversation_id)

    # 2. Lógica de Contexto do Aluno (Mantida igual)
    segmentos_busca = list(set([f['segmento'] for f in filhos]))
    mensagem_lower = mensagem_usuario.lower()
    filho_foco = None
    for filho in filhos:
        primeiro_nome = filho['nome'].split()[0].lower()
        if primeiro_nome in mensagem_lower:
            filho_foco = filho
            break
    if not filho_foco and len(filhos) == 1:
        filho_foco = filhos[0]

    # 3. Monta a Query (Mantida igual)
    query_para_vetor = mensagem_usuario
    if filho_foco:
        segmentos_busca = [filho_foco['segmento']]
        serie = filho_foco.get('serie', '')
        turma = filho_foco.get('turma', '')
        query_para_vetor = f"Comunicados escolares do {serie} turma {turma} sobre: {mensagem_usuario}"
        logger.info(f"Query Enriquecida: '{query_para_vetor}' (Foco: {filho_foco['nome']})")
    
    try:
        # Carrega contexto para a IA (passando o conversation_id)
        historico_contexto = _carregar_historico(user_email, conversation_id, 6)

        documentos_relevantes = vector_db.buscar_documentos(
            query=query_para_vetor, 
            filtro_segmentos=segmentos_busca,
            top_k=4
        )

        def gerar_stream():
            resposta_completa = ""
            for chunk in vector_db.gerar_resposta_ia_stream(
                pergunta=mensagem_usuario,
                contextos=documentos_relevantes,
                historico=historico_contexto,
                perfil_usuario=user_profile
            ):
                resposta_completa += chunk
                yield chunk
            
            # Salva resposta final com o ID da conversa
            _salvar_mensagem(user_email, 'assistant', resposta_completa, conversation_id)
        
        return Response(stream_with_context(gerar_stream()), mimetype='text/plain')

    except Exception as e:
        logger.error(f"Erro chat: {e}", exc_info=True)
        return jsonify({'error': 'Erro interno.'}), 500