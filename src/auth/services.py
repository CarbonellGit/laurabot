"""
Camada de Serviço (Service Layer) da Autenticação
"""

from google.cloud import firestore 
from src.core.database import db

RESPONSAVEIS_COLLECTION = 'responsaveis'

def verificar_ou_criar_responsavel(google_profile: dict) -> dict:
    """
    Verifica ou cria um responsável no Firestore.
    """
    
    if db is None:
        raise ConnectionError("Não foi possível conectar ao Firestore.")

    user_email = google_profile.get('email')
    if not user_email:
        raise ValueError("Perfil do Google não contém e-mail.")

    doc_ref = db.collection(RESPONSAVEIS_COLLECTION).document(user_email)
    doc = doc_ref.get()

    if doc.exists:
        user_data = doc.to_dict()
        user_data['email'] = user_email
        return user_data
    
    else:
        # Primeiro Acesso
        novo_responsavel = {
            'nome': google_profile.get('nome'),
            'google_id': google_profile.get('google_id'),
            'possui_cadastro_filhos': False, 
            'filhos': [],
            # Este campo causa erro na sessão se não for removido antes do return
            'criado_em': firestore.SERVER_TIMESTAMP 
        }
        
        doc_ref.set(novo_responsavel)
        
        # Prepara o objeto para retorno (Sessão)
        # Copiamos para não alterar o que foi enviado ao banco
        dados_sessao = novo_responsavel.copy()
        dados_sessao['email'] = user_email
        
        # Removemos o Timestamp (Sentinel) pois ele quebra a sessão do Flask
        if 'criado_em' in dados_sessao:
            del dados_sessao['criado_em']
            
        return dados_sessao
    
def obter_responsavel(email: str) -> dict:
    """
    Busca os dados atualizados de um responsável pelo e-mail.
    Útil para recarregar o perfil na tela de edição.
    """
    if db is None:
        return None

    doc_ref = db.collection(RESPONSAVEIS_COLLECTION).document(email)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        data['email'] = email
        return data
    return None  