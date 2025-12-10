"""
Módulo de Parsing e Inteligência de Documentos

Responsável por:
1. Extrair texto bruto de arquivos PDF.
2. Usar LLM (Gemini) para classificar o documento (Segmento, Série, Turma, Assunto).
"""

import json
import re
from io import BytesIO
from pypdf import PdfReader
from src.core.logger import get_logger
from src.core.ai import get_generative_model

logger = get_logger(__name__)

def extrair_texto_pdf(arquivo_storage) -> str:
    """
    Lê o PDF (objeto FileStorage ou BytesIO) e extrai todo o texto.
    Retorna string vazia em caso de erro.
    """
    try:
        # Lê o arquivo em memória
        # Se for BytesIO (Thread), lê direto. Se for FileStorage (Flask), lê via .read()
        if isinstance(arquivo_storage, BytesIO):
            pdf_bytes = arquivo_storage
        else:
            pdf_bytes = BytesIO(arquivo_storage.read())
            # Reseta ponteiro se for FileStorage, caso precise ser usado novamente
            if hasattr(arquivo_storage, 'seek'):
                arquivo_storage.seek(0)

        reader = PdfReader(pdf_bytes)
        texto_completo = ""

        for page in reader.pages:
            texto_pag = page.extract_text()
            if texto_pag:
                texto_completo += texto_pag + "\n"
        
        return texto_completo.strip()

    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF: {e}", exc_info=True)
        return ""

def _analisar_regex_fallback(nome_arquivo: str) -> dict:
    """
    Fallback: Tenta extrair metadados básicos via Regex se a IA falhar.
    """
    tags = {
        'segmento': 'TODOS', 
        'series': [], 
        'turmas': [],
        'assunto': 'Comunicado Geral'
    }
    nome_upper = nome_arquivo.upper()
    
    if 'EI' in nome_upper or 'INFANTIL' in nome_upper: tags['segmento'] = 'EI'
    elif 'AI' in nome_upper or 'ANOS INICIAIS' in nome_upper: tags['segmento'] = 'AI'
    elif 'AF' in nome_upper or 'ANOS FINAIS' in nome_upper: tags['segmento'] = 'AF'
    elif 'EM' in nome_upper or 'MEDIO' in nome_upper: tags['segmento'] = 'EM'
    
    # Regex simples para séries entre parênteses: (1) ou (5A)
    match_series = re.findall(r'\((\d+)[A-Z]?\)', nome_arquivo)
    if match_series:
        tags['series'] = [f"{num}º Ano/Série" for num in match_series]
        
    return tags

def analisar_metadados_ia(texto_completo: str, nome_arquivo: str) -> dict:
    """
    Envia o início do texto do PDF para o Gemini identificar metadados.
    Retorna um dicionário com: segmento, series, turmas, assunto.
    """
    if not texto_completo:
        return _analisar_regex_fallback(nome_arquivo)

    # Contexto limitado para economizar tokens
    texto_analise = texto_completo[:2500]

    prompt = f"""
    Analise o cabeçalho escolar e o texto abaixo extraído de um comunicado (PDF).
    Retorne APENAS um objeto JSON válido (sem markdown) com as chaves:
    
    - "segmento": Escolha UM entre ["EI", "AI", "AF", "EM", "TODOS"].
    - "series": Lista de strings (ex: ["1º Ano", "5º Ano"]). Se o texto disser "AI/5A", entenda como "5º Ano".
    - "turmas": Lista de strings (ex: ["A", "B"]). Se o texto disser "5A" ou "5º A", a turma é "A". Se não especificar, retorne [].
    - "assunto": Um resumo curto do título/tema (máx 5 palavras).

    Texto do arquivo ({nome_arquivo}):
    "{texto_analise}..."
    """

    try:
        # Usa a factory centralizada do src/core/ai.py
        model = get_generative_model()
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
            'turmas': dados_ia.get('turmas', []),
            'assunto': dados_ia.get('assunto', 'Comunicado')
        }
        
        logger.info(f"IA Classificou: {dados_finais}")
        return dados_finais

    except Exception as e:
        logger.warning(f"Falha na análise de IA ({e}). Usando fallback regex.")
        return _analisar_regex_fallback(nome_arquivo)