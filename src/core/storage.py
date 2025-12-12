"""
Módulo de Integração com Google Cloud Storage (Service Layer)

Responsável por upload, download e gerenciamento de arquivos.
"""

from datetime import timedelta
from typing import Optional, Tuple, Any
from google.cloud import storage
from flask import current_app
import uuid
import io

def _get_client() -> storage.Client:
    return storage.Client(project=current_app.config['GOOGLE_CLOUD_PROJECT'])

def generate_signed_url(blob_name: str, expiration: int = 3600) -> Optional[str]:
    """
    Gera uma Signed URL temporária para acesso seguro ao arquivo.
    Args:
        blob_name: ID interno do arquivo no GCS.
        expiration: Tempo em segundos (padrão 1 hora).
    """
    try:
        bucket_name = current_app.config.get('GCS_BUCKET_NAME')
        if not bucket_name: return None

        client = _get_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=expiration),
            method="GET"
        )
    except Exception as e:
        print(f"Erro ao gerar Signed URL: {e}")
        return None

def upload_file(arquivo_storage: Any, nome_original: str) -> Tuple[str, str]:
    """
    Faz o upload e retorna o NOME DO BLOB (ID interno).
    NÃO torna o arquivo público.
    
    Returns:
        tuple: (nome_blob, nome_blob) -> Mantendo tupla por compatibilidade, mas ambos são ID.
        FIXME: Ajustar chamadores para usar apenas o segundo retorno se possível ou renomear.
        Neste refactor, retornaremos (nome_blob, nome_blob) para forçar o uso do ID.
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

    # REMOVIDO: blob.make_public()
    
    return nome_blob, nome_blob

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

def delete_file(blob_name: str) -> None:
    """Remove arquivo do Bucket pelo nome do blob."""
    bucket_name = current_app.config.get('GCS_BUCKET_NAME')
    if not bucket_name or not blob_name: return

    try:
        # Se por acaso vier uma URL antiga completa, tenta extrair o blob name
        if f"/{bucket_name}/" in blob_name:
            nome_blob = blob_name.split(f"/{bucket_name}/")[-1]
        else:
            nome_blob = blob_name

        client = _get_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(nome_blob)
        blob.delete()
    except Exception as e:
        print(f"Erro ao deletar arquivo: {e}")
