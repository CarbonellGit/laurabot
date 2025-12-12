"""
Módulo de Banco de Dados Vetorial.
Refatorado para usar configuração centralizada de IA.
"""
from flask import current_app
from pinecone import Pinecone
from src.core.logger import get_logger
from src.core.ai import configurar_genai, get_embedding_model, get_generative_model
import google.generativeai as genai

logger = get_logger(__name__)

_pinecone_client = None

def _get_pinecone_client():
    global _pinecone_client
    if _pinecone_client is None:
        api_key = current_app.config.get('PINECONE_API_KEY')
        if not api_key:
            raise ValueError("PINECONE_API_KEY não configurada.")
        _pinecone_client = Pinecone(api_key=api_key)
    return _pinecone_client

def salvar_no_vetor(doc_id: str, texto_completo: str, metadados: dict):
    try:
        configurar_genai()
        # Gera Embedding
        resultado = genai.embed_content(
            model=get_embedding_model(),
            content=texto_completo.replace("\n", " "),
            task_type="retrieval_document"
        )
        vetor = resultado['embedding']

        pc = _get_pinecone_client()
        index = pc.Index(current_app.config.get('PINECONE_INDEX_NAME'))

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

def buscar_documentos(query: str, filtro_segmentos: list = None, top_k=4) -> list:
    if not query: return []
    try:
        configurar_genai()
        emb_res = genai.embed_content(
            model=get_embedding_model(),
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
            # Score mínimo mantido em 0.25 para não perder contexto relevante
            if match['score'] > 0.25:
                docs.append({
                    'id': match['id'],
                    'conteudo': match['metadata'].get('text', ''),
                    'fonte': match['metadata'].get('nome_arquivo', 'Arquivo'),
                    'link': match['metadata'].get('url_download', '#')
                })
        
        return docs

    except Exception as e:
        logger.error(f"Erro na busca: {e}", exc_info=True)
        return []

from typing import Generator, List, Dict, Any, Set
import re
from src.core.storage import generate_signed_url

def _stream_com_verificacao_links(generator_response, urls_permitidas: Set[str]) -> Generator[str, None, None]:
    """
    Filtra o stream de texto para garantir que apenas links permitidos sejam exibidos.
    Substitui links alucinados por [Link não verificado].
    """
    buffer = ""
    # Regex para capturar links Markdown completos: [Texto](URL)
    # A captura é feita em partes para permitir streaming
    
    for chunk in generator_response:
        text_chunk = chunk.text if hasattr(chunk, 'text') else str(chunk)
        if not text_chunk: continue
        
        buffer += text_chunk
        
        while True:
            # Procura por início de link '['
            start_link = buffer.find('[')
            if start_link == -1:
                # Não há inicio de link, podemos enviar tudo
                yield buffer
                buffer = ""
                break
            
            # Se achou '[', imprime até ele
            yield buffer[:start_link]
            buffer = buffer[start_link:]
            
            # Agora buffer começa com '[', tenta achar o fim do link ')'
            # Cuidado com links aninhados ou falsos, simplificando para o primeiro ')' após ']('
            match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', buffer)
            
            if match:
                # Temos um link completo
                texto_link = match.group(1)
                url_link = match.group(2)
                full_match = match.group(0)
                
                # Validação
                if url_link in urls_permitidas:
                    yield full_match
                else:
                    # Alucinação detectada ou link inválido
                    yield f"[{texto_link}](Link não verificado)"
                    
                # Remove o link processado do buffer
                buffer = buffer[len(full_match):]
            else:
                # Link incompleto ou apenas um bracket solto
                # Precisamos saber se é um link sendo formado ou não.
                # Se o buffer está muito grande e não fechou link, provavelmente não é link.
                # Mas para segurança do stream, vamos segurar apenas se parecer que está formando um link.
                
                # Casos: "[", "[Texto", "[Texto](", "[Texto](Url"
                
                # Se tivermos ']' e '(' depois mas sem ')', segura.
                # Se não tivermos ']' ainda, segura.
                
                # Limitador de buffer para evitar travar em caso de brackets soltos sem link
                if len(buffer) > 500: # Link muito longo ou falso positivo
                     yield buffer[0] # Solta o '[' e reprocessa o resto
                     buffer = buffer[1:]
                     continue
                
                # Sai do while para pegar mais chunks e completar o link
                break
    
    # Yield o que sobrou no buffer
    if buffer:
        yield buffer

def gerar_resposta_ia_stream(pergunta: str, contextos: list, historico: list = [], perfil_usuario: dict = {}) -> Generator[str, None, None]:
    """
    Gera resposta em STREAM (Yield) com Prompt Refinado e Guardrails de Links.
    """
    model = get_generative_model()
    
    texto_perfil = "PERFIL DO RESPONSÁVEL:\n"
    if perfil_usuario.get('filhos'):
        for f in perfil_usuario['filhos']:
            extra = " (Integral)" if f.get('integral') else ""
            texto_perfil += f"- Filho: {f['nome']} | Seg: {f['segmento']} | Série: {f.get('serie','')}{extra}\n"

    texto_historico = "HISTÓRICO:\n"
    for msg in historico:
        # Previne erro se content for None
        content = msg.get('content', '')
        if content:
            role = "Usuário" if msg.get('role') == 'user' else "Bot"
            texto_historico += f"{role}: {content[:300]}\n"

    texto_docs = ""
    urls_validas = set()

    if contextos:
        for doc in contextos:
            # doc['link'] traz o blob_name (ID interno) do Pinecone
            blob_name = doc.get('link')
            link_display = "#"
            
            if blob_name and blob_name != "#":
                # Gera Signed URL válida para este contexto
                signed_url = generate_signed_url(blob_name)
                if signed_url:
                    link_display = signed_url
                    urls_validas.add(signed_url)
            
            texto_docs += f"\n--- FONTE: {doc['fonte']} ({link_display}) ---\n{doc['conteudo']}\n"
    else:
        texto_docs = "Nenhum documento encontrado."

    # === PROMPT REFINADO (FIX) ===
    prompt_sistema = f"""
    Você é o LauraBot, assistente do Colégio Carbonell.
    Seja educado, prestativo e direto.
    
    {texto_perfil}
    {texto_historico}
    
    CONTEXTO (DOCUMENTOS ESCOLARES):
    {texto_docs}
    
    PERGUNTA DO USUÁRIO: "{pergunta}"
    
    DIRETRIZES DE RESPOSTA (SIGA RIGOROSAMENTE):
    1. Responda APENAS com base nos documentos fornecidos acima.
    2. Se a informação solicitada NÃO estiver nos documentos, diga educadamente: "Não encontrei essa informação nos comunicados recentes."
    3. REGRA DE OURO SOBRE LINKS:
       - SE e SOMENTE SE você encontrou a resposta no documento, cite a fonte no final usando o formato: [Nome do Arquivo](Link).
       - O Link DEVE ser EXATAMENTE um dos links listados nas FONTES acima.
       - NÃO altere, não encurte e não invente links. Copie e cole.
    """

    try:
        response = model.generate_content(prompt_sistema, stream=True)
        
        # Passa pelo verificador de links antes de entregar ao usuário
        for chunk_verificado in _stream_com_verificacao_links(response, urls_validas):
            yield chunk_verificado

    except Exception as e:
        logger.error(f"Erro na geração stream: {e}", exc_info=True)
        yield "Desculpe, tive um erro técnico."
