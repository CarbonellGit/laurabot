"""
Módulo de Configuração

Este módulo define a classe de configuração principal para a aplicação Flask.
Ele carrega variáveis de ambiente de um arquivo .env, garantindo que
segredos (como chKeys de API) não sejam expostos no código-fonte.

"""

import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env (se existir)
load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Permite OAuth em HTTP (apenas para desenvolvimento)  

class Config:
    """
    Classe de configuração base da aplicação.

    As configurações são carregadas das variáveis de ambiente.
    """

    # Chave secreta para o Flask (CRUCIAL para sessões)
    # Trocada por uma string segura e aleatória no .env
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-padrao-insegura'

    # Configurações do Google Cloud (do PRD)
    GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')

       # O Storage busca esta variável aqui, que por sua vez busca no .env
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
    
    # (Adicionaremos mais configurações aqui conforme necessário, 
    # como as credenciais do Firestore)

    # Configuração para o modo Debug
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1')

    # === Credenciais OAuth (Login RF-001) ===
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

 

    # === Credenciais de Serviço (Firestore RF-002) ===
    # O SDK do Google usa esta variável de ambiente automaticamente
    # Nós apenas a definimos no .env, não precisamos carregar no config.py
    # GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')