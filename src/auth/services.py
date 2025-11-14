"""
Camada de Serviço (Service Layer) da Autenticação

Este módulo contém a lógica de negócio relacionada à autenticação
e gerenciamento de perfis de responsáveis, desacoplando
as regras do PRD das rotas (controllers).
"""

# Importa a biblioteca principal do firestore
from google.cloud import firestore 

# Importa nossa instância (o 'db')
from src.core.database import db

# Define o nome da coleção no Firestore (RF-002)
RESPONSAVEIS_COLLECTION = 'responsaveis'

def verificar_ou_criar_responsavel(google_profile: dict) -> dict:
    """
    Verifica se um responsável (pai/mãe) já existe no Firestore
    baseado no e-mail do Google (RF-002).
    
    Se não existir, cria um novo perfil (RF-003).

    Args:
        google_profile (dict): O perfil do usuário obtido da sessão
                               (contém 'email', 'nome', 'google_id').

    Returns:
        dict: O perfil completo do usuário (do Firestore), incluindo
              o campo 'possui_cadastro_filhos'.
    """
    
    if db is None:
        raise ConnectionError("Não foi possível conectar ao Firestore.")

    user_email = google_profile.get('email')
    if not user_email:
        raise ValueError("Perfil do Google não contém e-mail.")

    # 1. Tenta buscar o documento do responsável pelo e-mail
    doc_ref = db.collection(RESPONSAVEIS_COLLECTION).document(user_email)
    doc = doc_ref.get()

    if doc.exists:
        # 2. (RF-002) Usuário encontrado. Retorna os dados do banco.
        user_data = doc.to_dict()
        user_data['email'] = user_email # Garante que o email (ID) esteja no dict
        return user_data
    
    else:
        # 3. (RF-003) Usuário não encontrado (Primeiro Acesso).
        print(f"Primeiro acesso detectado para: {user_email}. Criando perfil...")
        
        # Estrutura do novo documento no Firestore
        novo_responsavel = {
            'nome': google_profile.get('nome'),
            'google_id': google_profile.get('google_id'),
            
            # Campo chave para o RF-003:
            'possui_cadastro_filhos': False, 
            
            'filhos': [], # Lista de filhos (RF-004)
            
            # (Opcional) Data de criação
            'criado_em': firestore.SERVER_TIMESTAMP
        }
        
        # 4. Salva o novo responsável no Firestore
        doc_ref.set(novo_responsavel)
        
        # Retorna o perfil recém-criado
        novo_responsavel['email'] = user_email
        return novo_responsavel