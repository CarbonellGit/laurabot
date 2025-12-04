"""
Rotas do Módulo de Chat (RF-013 a RF-019)
Implementa o fluxo RAG: Contexto -> Busca Vetorial -> Geração de Resposta.
"""

from flask import render_template, session, redirect, url_for, request, jsonify
from . import chat_bp
from src.core import vector_db # Importa nosso novo cérebro

@chat_bp.route('/')
def index():
    """
    Rota principal da aplicação (O Chat).
    """
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    user_profile = session['user_profile']
    
    # Verifica cadastro (RF-003)
    if not user_profile.get('possui_cadastro_filhos', False):
         return redirect(url_for('auth_bp.cadastro_alunos'))

    # --- Saudação Personalizada (RF-013) ---
    nome_usuario = user_profile.get('nome', 'Responsável').split()[0]
    estudantes = user_profile.get('filhos', [])
    
    lista_nomes = []
    if estudantes:
        for est in estudantes:
            primeiro_nome = est['nome'].split()[0]
            lista_nomes.append(f"{primeiro_nome} ({est['segmento']})")
    
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

    return render_template('chat.html', mensagem_inicial=mensagem_inicial)


@chat_bp.route('/enviar', methods=['POST'])
def enviar_mensagem():
    """
    Recebe a pergunta, busca contexto e gera resposta com IA.
    """
    if 'user_profile' not in session:
        return jsonify({'response': 'Sessão expirada. Faça login novamente.'}), 401

    data = request.get_json()
    mensagem_usuario = data.get('message', '').strip()

    if not mensagem_usuario:
        return jsonify({'response': 'Por favor, digite uma pergunta.'})

    print(f"💬 Pergunta recebida: {mensagem_usuario}")

    # 1. Identificar Contexto (Segmentos dos Filhos)
    # Isso serve para filtrar no Pinecone e não trazer comunicados irrelevantes (ex: EI para pai de EM)
    user_profile = session['user_profile']
    filhos = user_profile.get('filhos', [])
    
    # Extrai lista de segmentos únicos (ex: ['EI', 'AF'])
    segmentos_usuario = list(set([f['segmento'] for f in filhos]))
    
    # Adiciona contexto de 'TODOS' implicitamente no vector_db, 
    # mas passamos os segmentos específicos aqui.
    print(f"🔍 Contexto do Usuário: {segmentos_usuario}")

    try:
        # 2. Busca Vetorial (Retrieval)
        documentos_relevantes = vector_db.buscar_documentos(
            query=mensagem_usuario,
            filtro_segmentos=segmentos_usuario,
            top_k=3 # Traz os 3 comunicados mais parecidos
        )

        # 3. Geração da Resposta (Generation)
        # Se não achou nada relevante, o próprio gerar_resposta_ia trata isso.
        resposta_ia = vector_db.gerar_resposta_ia(
            pergunta=mensagem_usuario,
            contextos=documentos_relevantes
        )

        return jsonify({'response': resposta_ia})

    except Exception as e:
        print(f"❌ Erro no Chat: {e}")
        return jsonify({'response': 'Desculpe, estou com uma instabilidade técnica momentânea. Tente novamente em alguns segundos.'})