"""
Módulo de Banco de Dados Vetorial (Pinecone + Gemini)

Responsável por:
1. Gerenciar o índice no Pinecone (Criação automática).
2. Gerar Embeddings usando Google Gemini.
3. Salvar e Buscar vetores (RAG).
"""

import os
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
    """
    Verifica se o índice do Pinecone existe. Se não, cria.
    Usamos dimensão 768 (padrão do modelo 'text-embedding-004' do Google).
    """
    pc = _get_pinecone_client()
    index_name = current_app.config.get('PINECONE_INDEX_NAME', 'laurabot-comunicados')

    # Lista índices existentes
    indexes = pc.list_indexes().names()

    if index_name not in indexes:
        print(f"--- Criando índice Pinecone: {index_name} ---")
        try:
            pc.create_index(
                name=index_name,
                dimension=768, 
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1" # Região do Free Tier
                )
            )
            # Aguarda a inicialização (pode levar alguns segundos)
            while not pc.describe_index(index_name).status['ready']:
                time.sleep(1)
            print("✅ Índice criado e pronto!")
        except Exception as e:
            print(f"Erro ao criar índice: {e}")
            raise e

def gerar_embedding(texto: str) -> list:
    """
    Usa o Google Gemini para converter texto em vetor (lista de floats).
    """
    _configurar_gemini()
    
    # Limpa o texto para evitar erros na API
    texto_limpo = texto.replace("\n", " ")
    
    try:
        # Modelo mais recente e eficiente de embeddings do Google
        resultado = genai.embed_content(
            model="models/text-embedding-004",
            content=texto_limpo,
            task_type="retrieval_document"
        )
        return resultado['embedding']
    except Exception as e:
        print(f"Erro ao gerar embedding: {e}")
        return []

def salvar_no_vetor(doc_id: str, texto_completo: str, metadados: dict):
    """
    Gera o vetor do texto e salva no Pinecone com os metadados.
    """
    # 1. Garante que a infraestrutura existe
    garantir_indice_existe()
    
    # 2. Gera o Embedding (Vetor)
    vetor = gerar_embedding(texto_completo)
    if not vetor:
        raise Exception("Falha ao gerar embedding do texto.")

    # 3. Conecta no Índice
    pc = _get_pinecone_client()
    index_name = current_app.config.get('PINECONE_INDEX_NAME', 'laurabot-comunicados')
    index = pc.Index(index_name)

    # 4. Upsert (Inserir ou Atualizar)
    # Pinecone espera: (id, vector, metadata)
    # Importante: Pinecone tem limite de 40kb para metadados. 
    # Não salvaremos o texto inteiro no metadado 'text' se for gigante.
    # Mas para comunicados de 1-2 páginas, geralmente cabe.
    
    # Cortamos o texto nos metadados por segurança (apenas para exibição/contexto)
    texto_safe = texto_completo[:30000] 

    registro = {
        'id': doc_id,
        'values': vetor,
        'metadata': {
            **metadados, # Espalha os metadados recebidos (segmento, série, link...)
            'text': texto_safe
        }
    }

    index.upsert(vectors=[registro])
    print(f"✅ Documento {doc_id} vetorizado e salvo no Pinecone!")