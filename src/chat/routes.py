"""
Rotas do Módulo de Chat

Refatorado para usar persistência no Firestore (chat_history)
e Logger estruturado.
"""

from flask import render_template, session, redirect, url_for, request, jsonify
from google.cloud import firestore
from . import chat_bp
from src.core import vector_db 
from src.core.database import db
from src.core.logger import get_logger

logger = get_logger(__name__)
COLLECTION_HISTORY = 'chat_history'

def _salvar_mensagem(user_email: str, role: str, content: str):
    """
    Salva uma mensagem individual no Firestore.
    """
    try:
        mensagem = {
            'user_email': user_email,
            'role': role,
            'content': content,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        # Adiciona na coleção 'chat_history'
        db.collection(COLLECTION_HISTORY).add(mensagem)
    except Exception as e:
        logger.error(f"Erro ao salvar mensagem no DB: {e}", exc_info=True)

def _carregar_historico(user_email: str, limite=10) -> list:
    """
    Recupera as últimas N mensagens do usuário para contexto.
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

@chat_bp.route('/')
def index():
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    user_profile = session['user_profile']
    user_email = user_profile['email']
    
    if not user_profile.get('possui_cadastro_filhos', False):
         return redirect(url_for('auth_bp.cadastro_alunos'))

    # --- Carrega Histórico Persistente ---
    historico_mensagens = _carregar_historico(user_email, limite=20)

    # --- Saudação Personalizada (apenas se não houver histórico) ---
    mensagem_inicial = None
    if not historico_mensagens:
        nome_usuario = user_profile.get('nome', 'Responsável').split()[0]
        estudantes = user_profile.get('filhos', [])
        
        lista_nomes = []
        if estudantes:
            for est in estudantes:
                primeiro_nome = est['nome'].split()[0]
                seg = est['segmento']
                extra = " (Integral)" if est.get('integral') else ""
                lista_nomes.append(f"{primeiro_nome} ({seg}{extra})")
        
        if len(lista_nomes) == 0:
            texto_filhos = "seus filhos"
        elif len(lista_nomes) == 1:
            texto_filhos = f"o estudante {lista_nomes[0]}"
        else:
            ultimo = lista_nomes.pop()
            texto_filhos = f"os estudantes {', '.join(lista_nomes)} e {ultimo}"

        mensagem_inicial = (
            f"Olá, {nome_usuario}! "
            f"Sou a assistente virtual do Colégio. Vi que você é responsável por {texto_filhos}. "
            "Pode me perguntar sobre datas, eventos, materiais ou qualquer comunicado enviado!"
        )

    return render_template('chat.html', 
                           historico=historico_mensagens, 
                           mensagem_inicial=mensagem_inicial)


@chat_bp.route('/enviar', methods=['POST'])
def enviar_mensagem():
    """
    Recebe a pergunta, busca contexto, recupera histórico do DB e gera resposta.
    """
    if 'user_profile' not in session:
        return jsonify({'response': 'Sessão expirada. Faça login novamente.'}), 401

    data = request.get_json()
    mensagem_usuario = data.get('message', '').strip()

    if not mensagem_usuario:
        return jsonify({'response': 'Por favor, digite uma pergunta.'})

    user_profile = session['user_profile']
    user_email = user_profile['email']
    filhos = user_profile.get('filhos', [])
    
    logger.info(f"Mensagem recebida de {user_email}: {mensagem_usuario[:50]}...")

    # 1. Salva a pergunta do usuário no Banco
    _salvar_mensagem(user_email, 'user', mensagem_usuario)

    # 2. Identificação Inteligente de Contexto (Filhos)
    # TODO: Na próxima fase (3), isso será feito via LLM, mas mantemos a lógica atual por enquanto.
    segmentos_busca = list(set([f['segmento'] for f in filhos]))
    mensagem_lower = mensagem_usuario.lower()
    
    for filho in filhos:
        primeiro_nome = filho['nome'].split()[0].lower()
        if primeiro_nome in mensagem_lower:
            segmentos_busca = [filho['segmento']]
            break 
            
    try:
        # 3. Carrega histórico recente do Banco para o Contexto da IA (RAG)
        historico_contexto = _carregar_historico(user_email, limite=6)

        # 4. Busca Vetorial (Retrieval)
        documentos_relevantes = vector_db.buscar_documentos(
            query=mensagem_usuario,
            filtro_segmentos=segmentos_busca,
            top_k=3 
        )

        # 5. Geração da Resposta (Generation)
        resposta_ia = vector_db.gerar_resposta_ia(
            pergunta=mensagem_usuario,
            contextos=documentos_relevantes,
            historico=historico_contexto,
            perfil_usuario=user_profile
        )

        # 6. Salva a resposta da IA no Banco
        _salvar_mensagem(user_email, 'assistant', resposta_ia)

        return jsonify({'response': resposta_ia})

    except Exception as e:
        logger.error(f"Erro no fluxo do Chat: {e}", exc_info=True)
        return jsonify({'response': 'Desculpe, estou com uma instabilidade técnica momentânea.'})