"""
Módulo de Parsing (Processamento de Arquivos)

Responsável por extrair texto de PDFs e interpretar metadados 
a partir do nome do arquivo (RF-009).
"""

import re
from pypdf import PdfReader
from io import BytesIO

def extrair_texto_pdf(arquivo_storage) -> str:
    """
    Recebe um arquivo (FileStorage do Flask), lê seu conteúdo PDF
    e retorna todo o texto extraído como uma única string.
    """
    try:
        # Lê o arquivo em memória
        pdf_bytes = BytesIO(arquivo_storage.read())
        
        # Cria o leitor
        reader = PdfReader(pdf_bytes)
        texto_completo = ""

        # Itera sobre as páginas e extrai o texto
        for page in reader.pages:
            texto_pag = page.extract_text()
            if texto_pag:
                texto_completo += texto_pag + "\n"
        
        # Volta o ponteiro do arquivo para o início (caso precise ser salvo depois)
        arquivo_storage.seek(0)
        
        return texto_completo.strip()

    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
        return ""

def analisar_nome_arquivo(nome_arquivo: str) -> dict:
    """
    RF-009: Analisa o nome do arquivo usando Regex para tentar
    identificar automaticamente o Segmento e a Série.
    
    Padrões esperados no nome: 
    - [EI], [AI], [AF], [EM] (Segmentos)
    - (1), (2), (3)... (Séries entre parênteses)
    """
    tags = {
        'segmento': None,
        'series': []
    }

    # 1. Tenta achar o Segmento (ex: "COM-AF-Viagem.pdf")
    nome_upper = nome_arquivo.upper()
    
    if 'EI' in nome_upper or 'INFANTIL' in nome_upper:
        tags['segmento'] = 'EI'
    elif 'AI' in nome_upper or 'ANOS INICIAIS' in nome_upper:
        tags['segmento'] = 'AI'
    elif 'AF' in nome_upper or 'ANOS FINAIS' in nome_upper:
        tags['segmento'] = 'AF'
    elif 'EM' in nome_upper or 'MEDIO' in nome_upper or 'MÉDIO' in nome_upper:
        tags['segmento'] = 'EM'
    else:
        tags['segmento'] = 'TODOS' # Padrão se não achar nada

    # 2. Tenta achar números de série entre parênteses ou soltos
    # Ex: (4) ou (4-5) ou apenas "4o ano"
    # Por enquanto, vamos fazer uma busca simples de dígitos
    # Isso pode ser refinado conforme os padrões de arquivo do colégio
    
    # Exemplo simples: Procura por "(1)", "(2)", etc.
    match_series = re.findall(r'\((\d+)\)', nome_arquivo)
    if match_series:
        # Mapeia números para nomes de série (Lógica simplificada)
        for num in match_series:
            tags['series'].append(f"{num}º Ano/Série")

    return tags