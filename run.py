"""
Ponto de Entrada da Aplicação (Runner)

Este script importa a "Application Factory" (create_app) do módulo 'src'
e inicia o servidor de desenvolvimento do Flask.

Para executar o servidor:
(Com o ambiente virtual .venv ativo)
$ python run.py
"""

from src import create_app

# Cria a instância da aplicação usando a factory
app = create_app()

if __name__ == "__main__":
    """
    Executa o servidor de desenvolvimento do Flask.
    
    'debug=app.config['DEBUG']' garante que o modo debug (com auto-reload)
    seja ativado se FLASK_DEBUG=True estiver no .env.
    """
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])