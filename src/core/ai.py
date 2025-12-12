"""
Configuração Centralizada de IA (GenAI).
Evita re-configuração e importações repetidas.
"""
from typing import Any
import google.generativeai as genai
from flask import current_app

_configurado: bool = False

def configurar_genai() -> None:
    """
    Configura a API Key do Gemini uma única vez.
    """
    global _configurado
    if _configurado:
        return

    api_key = current_app.config.get('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY não configurada.")
    
    genai.configure(api_key=api_key)
    _configurado = True

def get_embedding_model() -> str:
    configurar_genai()
    return "models/text-embedding-004"

def get_generative_model() -> genai.GenerativeModel:
    configurar_genai()
    return genai.GenerativeModel('gemini-2.5-flash')