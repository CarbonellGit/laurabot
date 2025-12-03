"""
Rotas do Módulo de Chat (RF-013 a RF-019)
"""

from flask import render_template, session, redirect, url_for, request, jsonify
from . import chat_bp

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

    # --- Lógica da Saudação Personalizada (RF-013) ---
    # Ex: "Olá! Vi aqui que você é responsável pelo Joao (AF) e pela Maria (EI)."
    
    nome_usuario = user_profile.get('nome', 'Responsável').split()[0]
    estudantes = user_profile.get('filhos', [])
    
    lista_nomes = []
    if estudantes:
        for est in estudantes:
            # Formata como "Nome (Segmento)"
            primeiro_nome = est['nome'].split()[0]
            lista_nomes.append(f"{primeiro_nome} ({est['segmento']})")
    
    if len(lista_nomes) == 0:
        texto_filhos = "seus filhos"
    elif len(lista_nomes) == 1:
        texto_filhos = f"o estudante {lista_nomes[0]}"
    else:
        # Junta com vírgulas e um "e" no final
        ultimo = lista_nomes.pop()
        texto_filhos = f"os estudantes {', '.join(lista_nomes)} e {ultimo}"

    mensagem_inicial = (
        f"Olá, {nome_usuario}! "
        f"Vi aqui que você é responsável por {texto_filhos}. "
        "Sobre qual comunicado ou evento você gostaria de saber hoje?"
    )

    return render_template('chat.html', mensagem_inicial=mensagem_inicial)


@chat_bp.route('/enviar', methods=['POST'])
def enviar_mensagem():
    """
    Recebe a mensagem do usuário via AJAX e retorna a resposta da IA.
    (Por enquanto, faz apenas um ECHO para teste).
    """
    if 'user_profile' not in session:
        return jsonify({'response': 'Sessão expirada. Faça login novamente.'}), 401

    data = request.get_json()
    mensagem_usuario = data.get('message', '')

    print(f"DEBUG: Mensagem recebida: {mensagem_usuario}")

    # --- AQUI ENTRARÁ A LÓGICA DA LLM (RF-015 a RF-017) ---
    # Simulando um "Echo" inteligente
    resposta_fake = f"Entendi que você perguntou sobre: '{mensagem_usuario}'. \n\n(Esta é uma resposta automática de teste. A integração com a IA será o próximo passo!)."

    return jsonify({'response': resposta_fake})