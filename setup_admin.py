"""
Script Utilitário: setup_admin.py
Use este script para promover um usuário a Administrador manualmente.
"""

from src import create_app
from src.core.database import db

# Inicializa a aplicação para carregar configurações e banco de dados
app = create_app()

def promover_usuario(email):
    print(f"--- Promovendo usuário: {email} ---")
    
    # Precisamos do contexto da aplicação para acessar o Firestore corretamente
    with app.app_context():
        # Referência ao documento do usuário na coleção 'responsaveis'
        doc_ref = db.collection('responsaveis').document(email)
        doc = doc_ref.get()
        
        if not doc.exists:
            print(f"❌ ERRO: O usuário '{email}' não foi encontrado no banco de dados.")
            print("DICA: Faça login na aplicação pelo navegador pelo menos uma vez para criar o registro inicial.")
            return

        # Atualiza o campo 'role' para 'admin'
        doc_ref.update({'role': 'admin'})
        
        print(f"✅ SUCESSO! O usuário '{email}' agora é um ADMIN.")
        print("⚠️  IMPORTANTE: Para que a mudança surta efeito, você precisa fazer LOGOUT e LOGIN novamente no navegador.")

if __name__ == "__main__":
    email_alvo = input("Digite o e-mail do usuário que será Admin: ").strip()
    promover_usuario(email_alvo)