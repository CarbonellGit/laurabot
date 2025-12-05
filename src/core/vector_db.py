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
            task_type="retrieval_query" 
        )
        return resultado['embedding']
    except Exception as e:
        print(f"Erro ao gerar embedding: {e}")
        return []

def salvar_no_vetor(doc_id: str, texto_completo: str, metadados: dict):
    """Gera o vetor do texto e salva no Pinecone."""
    garantir_indice_existe()
    
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

def excluir_do_vetor(doc_id: str):
    """
    Remove um documento do índice vetorial pelo ID.
    (Necessário para a exclusão lógica RF-012).
    """
    try:
        pc = _get_pinecone_client()
        index_name = current_app.config.get('PINECONE_INDEX_NAME', 'laurabot-comunicados')
        index = pc.Index(index_name)
        
        index.delete(ids=[doc_id])
        print(f"🗑️ Vetor {doc_id} removido do Pinecone.")
        
    except Exception as e:
        print(f"Erro ao excluir vetor: {e}")
        # Não damos raise aqui para não travar o fluxo de exclusão principal
        pass

def atualizar_metadados_vetor(doc_id: str, novos_metadados: dict):
    """
    Atualiza apenas os metadados de um vetor existente sem reprocessar o embedding.
    Útil para quando o admin muda o segmento/série do comunicado.
    """
    try:
        pc = _get_pinecone_client()
        index_name = current_app.config.get('PINECONE_INDEX_NAME', 'laurabot-comunicados')
        index = pc.Index(index_name)

        # O Pinecone permite update apenas de metadados
        index.update(id=doc_id, set_metadata=novos_metadados)
        print(f"✅ Metadados do vetor {doc_id} atualizados.")

    except Exception as e:
        print(f"Erro ao atualizar metadados do vetor: {e}")
        raise e

# === FUNÇÕES PARA O CHAT (RAG) ===

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

def gerar_resposta_ia(pergunta: str, contextos: list, historico: list = [], perfil_usuario: dict = {}) -> str:
    """
    Gera resposta considerando Contexto (RAG), Histórico (Memória) e Perfil do Usuário.
    """
    _configurar_gemini()
    
    # 1. Prepara dados do Perfil para o Prompt
    texto_perfil = "PERFIL DO RESPONSÁVEL (QUEM ESTÁ PERGUNTANDO):\n"
    if perfil_usuario and 'filhos' in perfil_usuario:
        for f in perfil_usuario['filhos']:
            integral_txt = " (Integral)" if f.get('integral') else ""
            texto_perfil += f"- Filho(a): {f['nome']} | Segmento: {f['segmento']} | Série: {f.get('serie','')} {integral_txt}\n"
    else:
        texto_perfil += "Perfil não identificado.\n"

    # 2. Prepara o Histórico para o Prompt
    texto_historico = ""
    if historico:
        texto_historico = "HISTÓRICO RECENTE DA CONVERSA:\n"
        for msg in historico:
            papel = "Usuário" if msg['role'] == 'user' else "LauraBot"
            # Limpa marcações markdown do histórico para não confundir
            conteudo_limpo = msg['content'].replace('\n', ' ')[:200] 
            texto_historico += f"{papel}: {conteudo_limpo}...\n"
    
    # 3. Prepara os Documentos (Contexto RAG)
    texto_contexto_docs = ""
    if contextos:
        for doc in contextos:
            texto_contexto_docs += f"\n--- DOCUMENTO: {doc['fonte']} | LINK: {doc['link']} ---\n{doc['conteudo']}\n"
    else:
        texto_contexto_docs = "Nenhum documento específico encontrado para esta busca."

    # 4. Prompt System (Cérebro do Bot)
    prompt_sistema = f"""
    Você é o LauraBot, assistente virtual oficial do Colégio Carbonell.
    
    {texto_perfil}
    
    {texto_historico}
    
    CONTEXTO DOS COMUNICADOS ENCONTRADOS AGORA:
    {texto_contexto_docs}
    
    PERGUNTA ATUAL DO USUÁRIO: 
    "{pergunta}"
    
    DIRETRIZES DE RACIOCÍNIO:
    1. **Identificação**: Se o usuário perguntar sobre "meu filho", "João", "a reunião", use o PERFIL e o HISTÓRICO para entender de quem/o que ele está falando. Ex: Se o histórico fala de reunião, e ele pergunta "que horas é?", é sobre a reunião citada antes.
    2. **Filtro de Fonte**: Responda APENAS com base nos COMUNICADOS ENCONTRADOS. Se a informação não estiver lá, diga que não sabe.
    3. **Integral**: Se o perfil do aluno for 'Integral' e houver documentos específicos de integral, priorize essas informações.
    
    DIRETRIZES DE RESPOSTA:
    - Seja direto e útil.
    - Se encontrou a resposta nos documentos, responda e no final adicione a seção "**Fonte(s):**" com o link markdown.
    - Se NÃO encontrou, diga educadamente e NÃO invente fontes.
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt_sistema)
        return response.text

    except Exception as e:
        print(f"Erro na geração da resposta: {e}")
        return "Desculpe, tive um problema ao processar sua resposta. Tente novamente em instantes."