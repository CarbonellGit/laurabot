"""
Módulo de Configuração (Blindado)

Define a classe de configuração principal. Implementa o padrão 'Fail Fast':
se uma variável crítica estiver faltando, a aplicação nem inicia.
"""

import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# Em produção (Cloud Run/App Engine), OAUTHLIB_INSECURE_TRANSPORT deve ser removido ou tratado.
# Mantemos aqui apenas se estivermos localmente, mas é bom ter atenção.
if os.environ.get('FLASK_DEBUG') == '1':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

class Config:
    """
    Classe de configuração base da aplicação.
    """

    # === SEGURANÇA CRÍTICA (Fail Fast) ===
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("ERRO CRÍTICO: 'SECRET_KEY' não encontrada no .env. A aplicação não pode iniciar insegura.")

    # === GOOGLE CLOUD & STORAGE ===
    GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
    
    # Validação opcional para evitar erros tardios de upload
    if not GCS_BUCKET_NAME:
        print("AVISO: 'GCS_BUCKET_NAME' não configurado. Uploads falharão.")

    # === IA & VETORES ===
    PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    
    if not PINECONE_API_KEY:
        print("AVISO: 'PINECONE_API_KEY' ausente. O Chatbot não funcionará.")
    if not GOOGLE_API_KEY:
        print("AVISO: 'GOOGLE_API_KEY' ausente. O Chatbot não funcionará.")

    PINECONE_INDEX_NAME = 'laurabot-comunicados'

    # === FLASK ===
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1')

    # === OAUTH (LOGIN) ===
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
         raise ValueError("ERRO CRÍTICO: Credenciais OAuth (CLIENT_ID/SECRET) ausentes.")