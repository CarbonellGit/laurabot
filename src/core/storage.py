"""
Módulo de Integração com Google Cloud Storage (Service Layer)

Responsável por upload, download e gerenciamento de arquivos.
"""

from google.cloud import storage
from flask import current_app
import uuid
import io

def _get_client():
    return storage.Client(project=current_app.config['GOOGLE_CLOUD_PROJECT'])

def upload_file(arquivo_storage, nome_original: str):
    """
    Faz o upload e retorna a URL pública E o nome do blob (ID interno).
    
    Returns:
        tuple: (url_publica, nome_blob)
    """
    bucket_name = current_app.config.get('GCS_BUCKET_NAME')
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME não configurado")

    client = _get_client()
    bucket = client.bucket(bucket_name)

    # Gera nome único
    nome_blob = f"{uuid.uuid4().hex}_{nome_original.replace(' ', '_')}"
    
    blob = bucket.blob(nome_blob)
    arquivo_storage.seek(0)
    blob.upload_from_file(arquivo_storage, content_type='application/pdf')

    try:
        blob.make_public()
    except Exception as e:
        print(f"Aviso: Não foi possível tornar público: {e}")

    return blob.public_url, nome_blob

def download_bytes_by_name(nome_blob: str) -> io.BytesIO:
    """
    Baixa o conteúdo de um arquivo usando o NOME DO BLOB (Seguro).
    """
    try:
        bucket_name = current_app.config.get('GCS_BUCKET_NAME')
        client = _get_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(nome_blob)
        
        arquivo_bytes = io.BytesIO()
        blob.download_to_file(arquivo_bytes)
        arquivo_bytes.seek(0)
        
        return arquivo_bytes
    except Exception as e:
        raise Exception(f"Falha ao baixar arquivo '{nome_blob}': {e}")

def delete_file(url_arquivo: str):
    """Remove arquivo do Bucket."""
    bucket_name = current_app.config.get('GCS_BUCKET_NAME')
    if not bucket_name or not url_arquivo: return

    try:
        nome_blob = url_arquivo.split(f"/{bucket_name}/")[-1]
        client = _get_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(nome_blob)
        blob.delete()
    except Exception as e:
        print(f"Erro ao deletar arquivo: {e}")