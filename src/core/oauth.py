"""
Módulo de Extensões - OAuth

Instancia o cliente Authlib, que será inicializado
pela Application Factory (em src/__init__.py).
"""

from authlib.integrations.flask_client import OAuth

# Instancia o objeto OAuth (ainda não configurado)
oauth = OAuth()