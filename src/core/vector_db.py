"""
Módulo de Banco de Dados Vetorial e IA (Pinecone + Gemini)

Responsável por:
1. Gerenciar vetores (Embeddings).
2. Buscar documentos relevantes (RAG).
3. Gerar respostas em linguagem natural.
"""

import time
from flask import current_app
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai

# Configuração Global (Lazy Loading)
_pinecone_client = None

def _get_pinecone_client():
    """Inicializa o cliente Pinecone (Singleton)."""
    global _pinecone_client
    if _pinecone_client is None:
        api_key = current_app.config.get('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY não configurada.")
        _pinecone_client = Pinecone(api_key=api_key)
    return _pinecone_client

def _configurar_gemini():
    """Configura a API do Google Gemini."""
    api_key = current_app.config.get('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY não configurada.")
    genai.configure(api_key=api_key)

def garantir_indice_existe():
    """Verifica se o índice do Pinecone existe. Se não, cria."""
    pc = _get_pinecone_client()
    index_name = current_app.config.get('PINECONE_INDEX_NAME', 'laurabot-comunicados')
    indexes = pc.list_indexes().names()

    if index_name not in indexes:
        print(f"--- Criando índice Pinecone: {index_name} ---")
        try:
            pc.create_index(
                name=index_name,
                dimension=768, 
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
            while not pc.describe_index(index_name).status['ready']:
                time.sleep(1)
            print("✅ Índice criado e pronto!")
        except Exception as e:
            print(f"Erro ao criar índice: {e}")
            raise e

def gerar_embedding(texto: str) -> list:
    """Usa o Google Gemini para converter texto em vetor."""
    _configurar_gemini()
    texto_limpo = texto.replace("\n", " ")
    try:
        resultado = genai.embed_content(
            model="models/text-embedding-004",
            content=texto_limpo,
            task_type="retrieval_query" # Mudamos para 'query' pois estamos buscando
        )
        return resultado['embedding']
    except Exception as e:
        print(f"Erro ao gerar embedding: {e}")
        return []

def salvar_no_vetor(doc_id: str, texto_completo: str, metadados: dict):
    """Gera o vetor do texto e salva no Pinecone."""
    garantir_indice_existe()
    
    # Para salvar, usamos task_type="retrieval_document" (interno na func acima se fosse parametrizavel, 
    # mas o modelo do Google é flexível. Para simplificar, usamos o embedding padrão).
    
    vetor = gerar_embedding(texto_completo)
    if not vetor:
        raise Exception("Falha ao gerar embedding do texto.")

    pc = _get_pinecone_client()
    index_name = current_app.config.get('PINECONE_INDEX_NAME', 'laurabot-comunicados')
    index = pc.Index(index_name)

    # Limita tamanho do texto nos metadados (Pinecone tem limite de 40kb)
    texto_safe = texto_completo[:30000] 

    registro = {
        'id': doc_id,
        'values': vetor,
        'metadata': {
            **metadados,
            'text': texto_safe
        }
    }
    index.upsert(vectors=[registro])
    print(f"✅ Documento {doc_id} vetorizado e salvo no Pinecone!")

# === NOVAS FUNÇÕES PARA O CHAT (RAG) ===

def buscar_documentos(query: str, filtro_segmentos: list = None, top_k=3) -> list:
    """
    Busca documentos no Pinecone similares à query, filtrando por segmento.
    """
    if not query: return []
    
    vetor_query = gerar_embedding(query)
    if not vetor_query: return []

    pc = _get_pinecone_client()
    index_name = current_app.config.get('PINECONE_INDEX_NAME', 'laurabot-comunicados')
    index = pc.Index(index_name)

    # Filtro de Metadados (MongoDB style)
    # Buscamos documentos onde 'segmento' está na lista de segmentos do usuário OU é 'TODOS'
    filtro_pinecone = {}
    
    if filtro_segmentos:
        # Adiciona 'TODOS' para garantir que comunicados gerais sempre apareçam
        lista_busca = list(set(filtro_segmentos + ['TODOS']))
        filtro_pinecone = {
            'segmento': {'$in': lista_busca}
        }

    try:
        resultados = index.query(
            vector=vetor_query,
            top_k=top_k,
            include_metadata=True,
            filter=filtro_pinecone
        )
        
        docs_encontrados = []
        for match in resultados['matches']:
            # Só aceita se a similaridade for relevante (> 0.4 é um bom chute inicial)
            if match['score'] > 0.40:
                docs_encontrados.append({
                    'id': match['id'],
                    'score': match['score'],
                    'conteudo': match['metadata'].get('text', ''),
                    'fonte': match['metadata'].get('nome_arquivo', 'Arquivo Desconhecido'),
                    'link': match['metadata'].get('url_download', '#')
                })
        
        return docs_encontrados

    except Exception as e:
        print(f"Erro na busca vetorial: {e}")
        return []

def gerar_resposta_ia(pergunta: str, contextos: list) -> str:
    """
    Monta o prompt com os contextos encontrados e pede a resposta ao Gemini.
    """
    _configurar_gemini()
    
    if not contextos:
        return "Não encontrei nenhum comunicado oficial sobre esse assunto específico. Por favor, tente reformular a pergunta ou entre em contato com a secretaria."

    # Monta o bloco de contexto para o prompt
    texto_contexto = ""
    fontes_usadas = set()
    
    for doc in contextos:
        texto_contexto += f"\n--- DOCUMENTO: {doc['fonte']} ---\n{doc['conteudo']}\n"
        # Guarda link markdown para citar no final
        fontes_usadas.add(f"[{doc['fonte']}]({doc['link']})")

    # Prompt Rigoroso (System Prompt)
    prompt_sistema = f"""
    Você é o LauraBot, assistente virtual oficial do Colégio Carbonell.
    Sua missão é responder dúvidas dos pais baseando-se EXCLUSIVAMENTE nos comunicados abaixo.
    
    CONTEXTO DOS COMUNICADOS:
    {texto_contexto}
    
    PERGUNTA DO USUÁRIO: 
    "{pergunta}"
    
    DIRETRIZES:
    1. Responda de forma educada, acolhedora e direta (em português do Brasil).
    2. Use APENAS as informações fornecidas no contexto acima. Se a informação não estiver lá, diga que não sabe. NÃO INVENTE.
    3. Se a resposta for encontrada, cite o nome do comunicado de referência.
    4. Formate a resposta usando Markdown (negrito para datas e pontos importantes).
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash') # Modelo rápido e barato
        response = model.generate_content(prompt_sistema)
        
        resposta_final = response.text
        
        # Adiciona as fontes no final (se já não estiverem citadas)
        resposta_final += "\n\n**Fontes consultadas:**\n" + "\n".join([f"📄 {f}" for f in fontes_usadas])
        
        return resposta_final

    except Exception as e:
        print(f"Erro na geração da resposta: {e}")
        return "Desculpe, tive um problema ao processar sua resposta. Tente novamente em instantes."