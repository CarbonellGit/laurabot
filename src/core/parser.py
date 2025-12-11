"""
Módulo de Parsing e Inteligência de Documentos

Responsável por:
1. Extrair texto bruto de arquivos PDF.
2. Usar LLM (Gemini) para classificar o documento (Segmento, Série, Turma, Assunto).
"""

import json
import re
from io import BytesIO
import pdfplumber
from src.core.logger import get_logger
from src.core.ai import get_generative_model

logger = get_logger(__name__)

def extrair_texto_pdf(arquivo_storage) -> str:
    """
    Lê o PDF e extrai texto preservando layout de tabelas via pdfplumber.
    """
    try:
        # pdfplumber exige arquivo em disco ou objeto file-like (BytesIO)
        if isinstance(arquivo_storage, BytesIO):
            pdf_file = arquivo_storage
        else:
            pdf_file = BytesIO(arquivo_storage.read())
            if hasattr(arquivo_storage, 'seek'):
                arquivo_storage.seek(0)

        texto_completo = ""
        
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                # extract_text(layout=True) tenta manter a posição visual (tabelas)
                # x_tolerance e y_tolerance podem ser ajustados se necessário
                texto_pag = page.extract_text(layout=True)
                if texto_pag:
                    texto_completo += texto_pag + "\n"
        
        return texto_completo.strip()

    except Exception as e:
        logger.error(f"Erro no pdfplumber: {e}", exc_info=True)
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
    Envia contexto para o Gemini identificar metadados.
    Prompt otimizado para ignorar rodapés e textos repetitivos.
    """
    if not texto_completo:
        return _analisar_regex_fallback(nome_arquivo)

    # Aumentamos um pouco o contexto pois pdfplumber mantém layout (mais espaçado)
    texto_analise = texto_completo[:3500]

    prompt = f"""
    ATENÇÃO: Você é um assistente administrativo escolar rigoroso.
    Analise o comunicado abaixo e extraia as informações solicitadas.
    
    REGRAS RÍGIDAS:
    1. IGNORE rodapés (endereços, telefones, CNPJ, frases de marketing da escola).
    2. Foco total em DATAS e PÚBLICO ALVO no cabeçalho ou corpo principal.
    3. Se houver um calendário/tabela, tente entender a estrutura visual.
    
    Retorne APENAS um JSON válido com as chaves:
    - "segmento": Escolha UM: ["EI", "AI", "AF", "EM", "TODOS"]. Se mencionar várias fases, use "TODOS".
    - "series": Lista de strings ex: ["1º Ano", "9º Ano"]. Se for para toda a escola/unidade, retorne [].
    - "turmas": Lista de strings ex: ["A", "B"]. Se não for específico de turma, [].
    - "assunto": Máx 5 palavras. Resumo objetivo do tema central.

    Arquivo: {nome_arquivo}
    Texto Extraído:
    "{texto_analise}..."
    """

    try:
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