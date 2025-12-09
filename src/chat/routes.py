"""
Rotas do Módulo de Chat

Atualizado com Query Expansion (Enriquecimento de Consulta)
para melhorar a precisão da busca vetorial por turma/série.
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

# ... (Manter as funções _salvar_mensagem e _carregar_historico IGUAIS ao anterior) ...
def _salvar_mensagem(user_email: str, role: str, content: str):
    try:
        db.collection(COLLECTION_HISTORY).add({
            'user_email': user_email,
            'role': role,
            'content': content,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem no DB: {e}", exc_info=True)

def _carregar_historico(user_email: str, limite=10) -> list:
    try:
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
        return historico[::-1]
    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {e}", exc_info=True)
        return []

# ... (Rota index mantém igual) ...
@chat_bp.route('/')
def index():
    if 'user_profile' not in session: return redirect(url_for('auth_bp.login'))
    user_profile = session['user_profile']
    historico = _carregar_historico(user_profile['email'], 20)
    mensagem_inicial = None
    if not historico:
        nome = user_profile.get('nome', '').split()[0]
        mensagem_inicial = f"Olá, {nome}! Como posso ajudar com os comunicados escolares hoje?"
    return render_template('chat.html', historico=historico, mensagem_inicial=mensagem_inicial)


@chat_bp.route('/enviar', methods=['POST'])
def enviar_mensagem():
    if 'user_profile' not in session:
        return jsonify({'error': 'Sessão expirada.'}), 401

    data = request.get_json()
    mensagem_usuario = data.get('message', '').strip()
    if not mensagem_usuario: return jsonify({'error': 'Vazio'}), 400

    user_profile = session['user_profile']
    user_email = user_profile['email']
    filhos = user_profile.get('filhos', []) # Lista de dicionários
    
    # 1. Salva pergunta original
    _salvar_mensagem(user_email, 'user', mensagem_usuario)

    # 2. Lógica de Contexto do Aluno (Query Expansion)
    segmentos_busca = list(set([f['segmento'] for f in filhos]))
    mensagem_lower = mensagem_usuario.lower()
    
    # Tenta identificar sobre qual filho o pai está falando
    filho_foco = None
    
    # Estratégia A: Busca por nome na mensagem
    for filho in filhos:
        primeiro_nome = filho['nome'].split()[0].lower()
        if primeiro_nome in mensagem_lower:
            filho_foco = filho
            break
    
    # Estratégia B: Se tem apenas 1 filho cadastrado, ele é o foco sempre
    if not filho_foco and len(filhos) == 1:
        filho_foco = filhos[0]

    # 3. Monta a Query Enriquecida (Isso vai para o Pinecone, mas o usuário não vê)
    query_para_vetor = mensagem_usuario
    
    if filho_foco:
        # Restringe a busca de segmento
        segmentos_busca = [filho_foco['segmento']]
        
        # ADICIONA CONTEXTO EXPLÍCITO NA QUERY
        # Isso força o vector search a dar match em documentos que tenham "5º Ano" ou "Turma A" no texto
        serie = filho_foco.get('serie', '')
        turma = filho_foco.get('turma', '')
        
        texto_extra = f" contexto escolar do aluno do {serie} turma {turma}"
        query_para_vetor = (
            f"Comunicados escolares do {serie} turma {turma} sobre: {mensagem_usuario}"
        )
        
        logger.info(f"Query Enriquecida: '{query_para_vetor}' (Foco: {filho_foco['nome']})")
    
    try:
        historico_contexto = _carregar_historico(user_email, 6)

        # Busca Vetorial usando a Query Enriquecida
        documentos_relevantes = vector_db.buscar_documentos(
            query=query_para_vetor, 
            filtro_segmentos=segmentos_busca,
            top_k=4  # Aumentei para 4 para dar mais chance
        )

        def gerar_stream():
            resposta_completa = ""
            # A IA recebe a pergunta original, mas os documentos vieram da busca turbinada
            for chunk in vector_db.gerar_resposta_ia_stream(
                pergunta=mensagem_usuario,
                contextos=documentos_relevantes,
                historico=historico_contexto,
                perfil_usuario=user_profile
            ):
                resposta_completa += chunk
                yield chunk
            _salvar_mensagem(user_email, 'assistant', resposta_completa)
        
        return Response(stream_with_context(gerar_stream()), mimetype='text/plain')

    except Exception as e:
        logger.error(f"Erro chat: {e}", exc_info=True)
        return jsonify({'error': 'Erro interno.'}), 500