"""
Rotas do Módulo de Chat
Implementa RAG com Memória de Conversação e Contexto de Perfil.
"""

from flask import render_template, session, redirect, url_for, request, jsonify
from . import chat_bp
from src.core import vector_db 

@chat_bp.route('/')
def index():
    if 'user_profile' not in session:
        return redirect(url_for('auth_bp.login'))

    user_profile = session['user_profile']
    
    if not user_profile.get('possui_cadastro_filhos', False):
         return redirect(url_for('auth_bp.cadastro_alunos'))

    # Limpa o histórico ao carregar a página (nova conversa)
    session['chat_history'] = [] 

    # --- Saudação Personalizada ---
    nome_usuario = user_profile.get('nome', 'Responsável').split()[0]
    estudantes = user_profile.get('filhos', [])
    
    lista_nomes = []
    if estudantes:
        for est in estudantes:
            primeiro_nome = est['nome'].split()[0]
            seg = est['segmento']
            # Adiciona indicador visual se for integral
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

    return render_template('chat.html', mensagem_inicial=mensagem_inicial)


@chat_bp.route('/enviar', methods=['POST'])
def enviar_mensagem():
    """
    Recebe a pergunta, busca contexto, recupera histórico e gera resposta.
    """
    if 'user_profile' not in session:
        return jsonify({'response': 'Sessão expirada. Faça login novamente.'}), 401

    data = request.get_json()
    mensagem_usuario = data.get('message', '').strip()

    if not mensagem_usuario:
        return jsonify({'response': 'Por favor, digite uma pergunta.'})

    print(f"💬 Pergunta recebida: {mensagem_usuario}")

    # 1. Recupera Perfil e Histórico
    user_profile = session['user_profile']
    filhos = user_profile.get('filhos', [])
    
    # Inicializa histórico se não existir
    if 'chat_history' not in session:
        session['chat_history'] = []

    # 2. Identificação Inteligente de Contexto (Filhos)
    segmentos_busca = list(set([f['segmento'] for f in filhos]))
    mensagem_lower = mensagem_usuario.lower()
    
    # Tenta achar qual filho foi mencionado para filtrar a BUSCA (Retrieval)
    for filho in filhos:
        primeiro_nome = filho['nome'].split()[0].lower()
        if primeiro_nome in mensagem_lower:
            segmentos_busca = [filho['segmento']]
            break 
            
    try:
        # 3. Busca Vetorial (Retrieval)
        # Trazemos documentos baseados na pergunta ATUAL
        documentos_relevantes = vector_db.buscar_documentos(
            query=mensagem_usuario,
            filtro_segmentos=segmentos_busca,
            top_k=3 
        )

        # 4. Geração da Resposta (Generation) com MEMÓRIA
        # Passamos o histórico e o perfil completo para a IA entender o contexto
        resposta_ia = vector_db.gerar_resposta_ia(
            pergunta=mensagem_usuario,
            contextos=documentos_relevantes,
            historico=session['chat_history'],
            perfil_usuario=user_profile
        )

        # 5. Atualiza a Memória (Mantém as últimas 6 mensagens / 3 turnos para não estourar sessão)
        historico_atual = session['chat_history']
        historico_atual.append({'role': 'user', 'content': mensagem_usuario})
        historico_atual.append({'role': 'assistant', 'content': resposta_ia})
        
        # Mantém apenas os últimos 6 itens
        if len(historico_atual) > 6:
            historico_atual = historico_atual[-6:]
            
        session['chat_history'] = historico_atual
        session.modified = True # Força salvamento do cookie

        return jsonify({'response': resposta_ia})

    except Exception as e:
        print(f"❌ Erro no Chat: {e}")
        return jsonify({'response': 'Desculpe, estou com uma instabilidade técnica momentânea.'})