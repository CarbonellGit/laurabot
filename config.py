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
    
    # (Adicionaremos mais configurações aqui conforme necessário, 
    # como as credenciais do Firestore)

    # Configuração para o modo Debug
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1')