"""
Camada de Serviço (Service Layer) da Autenticação

Responsável pela lógica de banco de dados dos usuários,
agora com suporte a Roles e Logging estruturado.
"""

from google.cloud import firestore
from src.core.database import db
from src.core.logger import get_logger

# Inicializa o logger para este módulo
logger = get_logger(__name__)

RESPONSAVEIS_COLLECTION = 'responsaveis'

def verificar_ou_criar_responsavel(google_profile: dict) -> dict:
    """
    Verifica ou cria um responsável no Firestore.
    Define automaticamente a role='user' para novos cadastros.
    """
    
    if db is None:
        logger.critical("Tentativa de acesso ao Firestore falhou: Cliente DB é None.")
        raise ConnectionError("Não foi possível conectar ao Firestore.")

    user_email = google_profile.get('email')
    if not user_email:
        logger.error("Perfil do Google recebido sem e-mail.")
        raise ValueError("Perfil do Google não contém e-mail.")

    doc_ref = db.collection(RESPONSAVEIS_COLLECTION).document(user_email)
    
    try:
        doc = doc_ref.get()

        if doc.exists:
            user_data = doc.to_dict()
            user_data['email'] = user_email
            
            # Garante que campos novos existam em usuários antigos (Backward Compatibility)
            if 'role' not in user_data:
                user_data['role'] = 'user' 
            
            logger.info(f"Login efetuado: {user_email} (Role: {user_data.get('role')})")
            return user_data
        
        else:
            # Primeiro Acesso (Novo Usuário)
            logger.info(f"Criando novo usuário: {user_email}")
            
            novo_responsavel = {
                'nome': google_profile.get('nome'),
                'google_id': google_profile.get('google_id'),
                'role': 'user',  # Padrão de segurança: ninguém nasce admin
                'possui_cadastro_filhos': False, 
                'filhos': [],
                'criado_em': firestore.SERVER_TIMESTAMP 
            }
            
            doc_ref.set(novo_responsavel)
            
            # Prepara objeto para sessão (removendo Timestamp)
            dados_sessao = novo_responsavel.copy()
            dados_sessao['email'] = user_email
            if 'criado_em' in dados_sessao:
                del dados_sessao['criado_em']
                
            return dados_sessao

    except Exception as e:
        logger.error(f"Erro ao processar login para {user_email}: {e}", exc_info=True)
        raise e
    
def obter_responsavel(email: str) -> dict:
    """
    Busca os dados atualizados de um responsável.
    """
    if db is None:
        return None

    try:
        doc_ref = db.collection(RESPONSAVEIS_COLLECTION).document(email)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            data['email'] = email
            return data
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar responsável {email}: {e}", exc_info=True)
        return None