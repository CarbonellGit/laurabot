"""
Módulo de Banco de Dados Vetorial e IA (Pinecone + Gemini)

Responsável por Embeddings, RAG e Geração de Texto.
Agora com suporte a Streaming (yield) e Logging estruturado.
"""

import time
from flask import current_app
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai
from src.core.logger import get_logger

logger = get_logger(__name__)

# Configuração Global (Lazy Loading)
_pinecone_client = None

def _get_pinecone_client():
    global _pinecone_client
    if _pinecone_client is None:
        api_key = current_app.config.get('PINECONE_API_KEY')
        if not api_key:
            logger.critical("PINECONE_API_KEY não configurada.")
            raise ValueError("PINECONE_API_KEY não configurada.")
        _pinecone_client = Pinecone(api_key=api_key)
    return _pinecone_client

def _configurar_gemini():
    api_key = current_app.config.get('GOOGLE_API_KEY')
    if not api_key:
        logger.critical("GOOGLE_API_KEY não configurada.")
        raise ValueError("GOOGLE_API_KEY não configurada.")
    genai.configure(api_key=api_key)

def salvar_no_vetor(doc_id: str, texto_completo: str, metadados: dict):
    """Gera o vetor do texto e salva no Pinecone."""
    try:
        _configurar_gemini()
        # Gera Embedding
        resultado = genai.embed_content(
            model="models/text-embedding-004",
            content=texto_completo.replace("\n", " "),
            task_type="retrieval_document"
        )
        vetor = resultado['embedding']

        pc = _get_pinecone_client()
        index_name = current_app.config.get('PINECONE_INDEX_NAME')
        index = pc.Index(index_name)

        # Truncate seguro para metadados (limite do Pinecone 40kb)
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
        logger.info(f"Documento vetorizado e salvo: {doc_id}")

    except Exception as e:
        logger.error(f"Erro ao salvar no vetor: {e}", exc_info=True)
        raise e

def excluir_do_vetor(doc_id: str):
    try:
        pc = _get_pinecone_client()
        index = pc.Index(current_app.config.get('PINECONE_INDEX_NAME'))
        index.delete(ids=[doc_id])
        logger.info(f"Vetor removido: {doc_id}")
    except Exception as e:
        logger.error(f"Erro ao excluir vetor {doc_id}: {e}", exc_info=True)

def atualizar_metadados_vetor(doc_id: str, novos_metadados: dict):
    try:
        pc = _get_pinecone_client()
        index = pc.Index(current_app.config.get('PINECONE_INDEX_NAME'))
        index.update(id=doc_id, set_metadata=novos_metadados)
        logger.info(f"Metadados atualizados: {doc_id}")
    except Exception as e:
        logger.error(f"Erro ao atualizar metadados {doc_id}: {e}", exc_info=True)
        raise e

def buscar_documentos(query: str, filtro_segmentos: list = None, top_k=4) -> list: # Aumentei top_k para 4
    if not query: return []
    try:
        _configurar_gemini()
        emb_res = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query"
        )
        vetor_query = emb_res['embedding']

        pc = _get_pinecone_client()
        index = pc.Index(current_app.config.get('PINECONE_INDEX_NAME'))

        filtro_pinecone = {}
        if filtro_segmentos:
            lista_busca = list(set(filtro_segmentos + ['TODOS']))
            filtro_pinecone = {'segmento': {'$in': lista_busca}}

        resultados = index.query(
            vector=vetor_query,
            top_k=top_k,
            include_metadata=True,
            filter=filtro_pinecone
        )
        
        docs = []
        logger.info(f"--- RESULTADOS DA BUSCA PARA: '{query}' ---")
        
        for match in resultados['matches']:
            score = match['score']
            doc_id = match['id']
            # LOG DE DEBUG IMPORTANTE: Mostra o que o Pinecone achou e a nota
            logger.info(f"Arquivo: {doc_id} | Score: {score:.4f}")

            # AJUSTE DA RÉGUA: Baixamos de 0.40 para 0.25
            # Isso permite matches "menos perfeitos" mas semanticamente úteis
            if score > 0.40:
                docs.append({
                    'id': doc_id,
                    'conteudo': match['metadata'].get('text', ''),
                    'fonte': match['metadata'].get('nome_arquivo', 'Arquivo'),
                    'link': match['metadata'].get('url_download', '#')
                })
        
        if not docs:
            logger.warning("Nenhum documento atingiu o score mínimo de 0.40")

        return docs

    except Exception as e:
        logger.error(f"Erro na busca: {e}", exc_info=True)
        return []

def gerar_resposta_ia_stream(pergunta: str, contextos: list, historico: list = [], perfil_usuario: dict = {}):
    """
    Gera resposta em STREAM (Yield) considerando Contexto e Histórico.
    """
    _configurar_gemini()
    
    # Montagem do Prompt (Mesma lógica da fase anterior)
    texto_perfil = "PERFIL DO RESPONSÁVEL:\n"
    if perfil_usuario.get('filhos'):
        for f in perfil_usuario['filhos']:
            extra = " (Integral)" if f.get('integral') else ""
            texto_perfil += f"- Filho: {f['nome']} | Seg: {f['segmento']} | Série: {f.get('serie','')}{extra}\n"

    texto_historico = "HISTÓRICO:\n"
    for msg in historico:
        role = "Usuário" if msg['role'] == 'user' else "Bot"
        texto_historico += f"{role}: {msg['content'][:300]}\n"

    texto_docs = ""
    if contextos:
        for doc in contextos:
            texto_docs += f"\n--- FONTE: {doc['fonte']} ({doc['link']}) ---\n{doc['conteudo']}\n"
    else:
        texto_docs = "Nenhum documento encontrado."

    prompt_sistema = f"""
    Você é o LauraBot, assistente do Colégio Carbonell.
    
    {texto_perfil}
    {texto_historico}
    
    CONTEXTO (DOCUMENTOS):
    {texto_docs}
    
    PERGUNTA: "{pergunta}"
    
    Responda com base SOMENTE nos documentos. Se não souber, diga.
    Cite a fonte com link Markdown no final: [Nome Arquivo](URL).
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        # Habilita o streaming na API do Google
        response = model.generate_content(prompt_sistema, stream=True)
        
        for chunk in response:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        logger.error(f"Erro na geração stream: {e}", exc_info=True)
        yield "Desculpe, tive um erro técnico."