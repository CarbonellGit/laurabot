"""
Módulo de Integração com Google Cloud Storage (Service Layer)

Responsável por upload, download e gerenciamento de URLs públicas
dos arquivos PDF (RF-008 e RF-019).
"""

from google.cloud import storage
from flask import current_app
import uuid

def _get_client():
    """Retorna uma instância do cliente Storage."""
    return storage.Client(project=current_app.config['GOOGLE_CLOUD_PROJECT'])

def upload_file(arquivo_storage, nome_original: str) -> str:
    """
    Faz o upload de um arquivo para o Bucket configurado e torna-o público.

    Args:
        arquivo_storage: O objeto FileStorage do Flask (request.files).
        nome_original (str): Nome original do arquivo para referência.

    Returns:
        str: A URL pública (https) para acessar o arquivo.
    """
    bucket_name = current_app.config.get('GCS_BUCKET_NAME')
    
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME não configurado no .env")

    client = _get_client()
    bucket = client.bucket(bucket_name)

    # Gera um nome único para evitar sobrescrita (UUID + Nome original limpo)
    extensao = nome_original.split('.')[-1]
    nome_unico = f"{uuid.uuid4().hex}_{nome_original.replace(' ', '_')}"
    
    blob = bucket.blob(nome_unico)

    # Importante: Volta o ponteiro do arquivo para o início antes de ler
    arquivo_storage.seek(0)
    
    # Upload do conteúdo
    blob.upload_from_file(arquivo_storage, content_type='application/pdf')

    # Torna o arquivo público para leitura (RF-019: Link de download)
    try:
        blob.make_public()
    except Exception as e:
        print(f"Aviso: Não foi possível tornar público automaticamente: {e}")

    return blob.public_url

def delete_file(url_arquivo: str):
    """
    Remove um arquivo do Bucket (RF-011).
    Extrai o nome do blob da URL pública.
    """
    bucket_name = current_app.config.get('GCS_BUCKET_NAME')
    if not bucket_name or not url_arquivo:
        return

    # Tenta extrair o nome do blob da URL padrão do GCS
    try:
        nome_blob = url_arquivo.split(f"/{bucket_name}/")[-1]
        
        client = _get_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(nome_blob)
        blob.delete()
        print(f"Arquivo removido do Storage: {nome_blob}")
        
    except Exception as e:
        print(f"Erro ao deletar arquivo do Storage: {e}")