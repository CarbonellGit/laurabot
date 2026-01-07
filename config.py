"""
Módulo de Configuração (Blindado)

Define a classe de configuração principal. Implementa o padrão 'Fail Fast':
se uma variável crítica estiver faltando, a aplicação nem inicia.
"""

import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# === CORREÇÃO PARA LOGIN GOOGLE LOCALHOST ===
# O Authlib/Google exige HTTPS por padrão. Isso permite HTTP apenas se estivermos em DEBUG.
# Em produção (Cloud Run), isso é ignorado automaticamente.
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

    PINECONE_INDEX_NAME = os.environ.get('PINECONE_INDEX_NAME', 'laurabot-comunicados')

    # === FLASK & SEGURANÇA ===
    # Detecta ambiente: Se FLASK_DEBUG for '1' ou 'True', estamos em DEV.
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1')
    
    # Hardening de Sessão
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax' # Necessário para o redirect do Google funcionar bem
    
    # A MÁGICA DO LOGIN: 
    # Em Produção (False) -> Exige HTTPS (True)
    # Em Localhost (True) -> Permite HTTP (False)
    SESSION_COOKIE_SECURE = not DEBUG 

    # === OAUTH (LOGIN) ===
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
         raise ValueError("ERRO CRÍTICO: Credenciais OAuth (CLIENT_ID/SECRET) ausentes.")