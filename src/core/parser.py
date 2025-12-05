"""
Módulo de Parsing e Inteligência de Documentos

Responsável por:
1. Extrair texto bruto de arquivos PDF.
2. Usar LLM (Gemini) para classificar o documento (Segmento, Série, Assunto).
"""

import json
import re
from io import BytesIO
from pypdf import PdfReader
from flask import current_app
import google.generativeai as genai
from src.core.logger import get_logger

logger = get_logger(__name__)

def extrair_texto_pdf(arquivo_storage) -> str:
    """
    Lê o PDF e extrai todo o texto.
    Retorna string vazia em caso de erro.
    """
    try:
        # Lê o arquivo em memória
        pdf_bytes = BytesIO(arquivo_storage.read())
        reader = PdfReader(pdf_bytes)
        texto_completo = ""

        for page in reader.pages:
            texto_pag = page.extract_text()
            if texto_pag:
                texto_completo += texto_pag + "\n"
        
        # Reseta o ponteiro para que possa ser salvo no Storage depois
        arquivo_storage.seek(0)
        
        return texto_completo.strip()

    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF: {e}", exc_info=True)
        return ""

def _configurar_gemini():
    """Configura a API Key do Gemini."""
    api_key = current_app.config.get('GOOGLE_API_KEY')
    if not api_key:
        logger.error("GOOGLE_API_KEY não configurada para o Parser.")
        return False
    genai.configure(api_key=api_key)
    return True

def _analisar_regex_fallback(nome_arquivo: str) -> dict:
    """
    Fallback: Tenta extrair metadados básicos via Regex se a IA falhar.
    """
    tags = {'segmento': 'TODOS', 'series': [], 'assunto': 'Comunicado Geral'}
    nome_upper = nome_arquivo.upper()
    
    if 'EI' in nome_upper or 'INFANTIL' in nome_upper: tags['segmento'] = 'EI'
    elif 'AI' in nome_upper or 'ANOS INICIAIS' in nome_upper: tags['segmento'] = 'AI'
    elif 'AF' in nome_upper or 'ANOS FINAIS' in nome_upper: tags['segmento'] = 'AF'
    elif 'EM' in nome_upper or 'MEDIO' in nome_upper: tags['segmento'] = 'EM'
    
    match_series = re.findall(r'\((\d+)\)', nome_arquivo)
    if match_series:
        tags['series'] = [f"{num}º Ano/Série" for num in match_series]
        
    return tags

def analisar_metadados_ia(texto_completo: str, nome_arquivo: str) -> dict:
    """
    Envia o início do texto do PDF para o Gemini identificar metadados.
    Retorna um dicionário com: segmento, series (lista), assunto.
    """
    if not _configurar_gemini() or not texto_completo:
        return _analisar_regex_fallback(nome_arquivo)

    # Pegamos apenas os primeiros 2000 caracteres (cabeçalho/início) para economizar tokens e tempo
    texto_analise = texto_completo[:2000]

    prompt = f"""
    Analise o cabeçalho escolar e o texto abaixo extraído de um comunicado (PDF).
    Extraia e retorne APENAS um objeto JSON (sem markdown) com as chaves:
    
    - "segmento": Escolha UM entre ["EI", "AI", "AF", "EM", "TODOS"]. 
      (EI=Infantil, AI=1º ao 5º ano, AF=6º ao 9º ano, EM=Médio). Se não for claro ou for para todos, use "TODOS".
    - "series": Lista de strings com as séries citadas (ex: ["1º Ano", "3ª Série"]). Se for para todo o segmento, retorne lista vazia [].
    - "assunto": Um resumo curto do título/tema (máx 5 palavras).

    Texto do arquivo ({nome_arquivo}):
    "{texto_analise}..."
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Generation Config força resposta JSON (feature nova do Gemini 1.5/2.0, 
        # mas aqui vamos usar prompt engineering clássico para garantir compatibilidade)
        response = model.generate_content(prompt)
        raw_text = response.text.strip()

        # Limpeza básica caso o modelo devolva ```json ... ```
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`").replace("json", "").strip()
        
        dados_ia = json.loads(raw_text)
        
        # Normalização de segurança
        dados_finais = {
            'segmento': dados_ia.get('segmento', 'TODOS'),
            'series': dados_ia.get('series', []),
            'assunto': dados_ia.get('assunto', 'Comunicado')
        }
        
        logger.info(f"IA Classificou: {dados_finais}")
        return dados_finais

    except Exception as e:
        logger.warning(f"Falha na análise de IA ({e}). Usando fallback regex.")
        return _analisar_regex_fallback(nome_arquivo)