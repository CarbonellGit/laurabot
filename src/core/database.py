"""
Módulo de Conexão com o Banco de Dados (Core)

Inicializa o cliente do Google Firestore, que será usado
pelos "Service Layers" da aplicação.
"""

from google.cloud import firestore

# Inicializa o cliente do Firestore.
# O SDK buscará automaticamente as credenciais na variável de ambiente
# 'GOOGLE_APPLICATION_CREDENTIALS' (definida no .env).
try:
    db = firestore.Client()
    print("Conexão com o Firestore estabelecida com sucesso.")
except Exception as e:
    print(f"ERRO AO CONECTAR COM O FIRESTORE: {e}")
    # Em um app real, poderíamos usar um logger aqui
    db = None