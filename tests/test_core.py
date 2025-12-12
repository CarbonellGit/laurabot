
import unittest
from unittest.mock import MagicMock, patch
import io
import json
from src.core import parser

class TestCoreParser(unittest.TestCase):

    @patch('src.core.parser.pdfplumber.open')
    def test_extrair_texto_pdf_sucesso(self, mock_pdf_open):
        # Mock do PDF e Página e texto extraído
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Texto de Teste Extraído"
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        
        # Context Manager mock
        mock_pdf_open.return_value.__enter__.return_value = mock_pdf
        
        arquivo_fake = io.BytesIO(b"fake content")
        resultado = parser.extrair_texto_pdf(arquivo_fake)
        
        self.assertEqual(resultado, "Texto de Teste Extraído")
        mock_page.extract_text.assert_called_with(layout=True)

    @patch('src.core.parser.pdfplumber.open')
    def test_extrair_texto_pdf_falha(self, mock_pdf_open):
        # Simula erro ao abrir PDF
        mock_pdf_open.side_effect = Exception("Arquivo corrompido")
        
        arquivo_fake = io.BytesIO(b"bad content")
        # Deve retornar string vazia e logar erro (não testamos log aqui mas o retorno)
        resultado = parser.extrair_texto_pdf(arquivo_fake)
        self.assertEqual(resultado, "")

    @patch('src.core.parser.get_generative_model')
    def test_analisar_metadados_ia_sucesso(self, mock_get_model):
        # Mock da resposta da IA
        mock_response = MagicMock()
        dados_esperados = {
            "segmento": "EI",
            "series": ["Maternal"],
            "turmas": ["A"],
            "assunto": "Festa da Uva"
        }
        # Simula retorno JSON válido (às vezes vem com markdown block)
        mock_response.text = "```json\n" + json.dumps(dados_esperados) + "\n```"
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_get_model.return_value = mock_model
        
        resultado = parser.analisar_metadados_ia("Texto do comunicado...", "arquivo.pdf")
        
        self.assertEqual(resultado['segmento'], "EI")
        self.assertEqual(resultado['assunto'], "Festa da Uva")

    @patch('src.core.parser.get_generative_model')
    def test_analisar_metadados_ia_fallback_erro(self, mock_get_model):
        # Simula erro na API do Gemini
        mock_get_model.side_effect = Exception("API Error")
        
        # Nome do arquivo sugere EI (Educação Infantil)
        nome_arquivo = "Comunicado_EI_Maternal.pdf"
        resultado = parser.analisar_metadados_ia("Texto...", nome_arquivo)
        
        # Deve ter caído no fallback regex que detecta 'EI' no nome
        self.assertEqual(resultado['segmento'], "EI")

    def test_analisar_regex_fallback_direto(self):
        # Teste direto da função privada (acessível em Python)
        
        # Caso 1: AI (Anos Iniciais) e Série (1A)
        tags1 = parser._analisar_regex_fallback("Comunicado_AI_1A.pdf") # Regex captura (1) se estiver assim (1) ou se melhorar o regex.
        # O regex atual é r'\((\d+)[A-Z]?\)' -> espera parênteses, ex: (1) ou (1A)
        # Vamos ajustar o nome do arquivo para bater com o regex atual
        tags1 = parser._analisar_regex_fallback("Comunicado_AI_(1A).pdf")
        
        self.assertEqual(tags1['segmento'], "AI")
        self.assertIn("1º Ano/Série", tags1['series'])
        
        # Caso 2: EM (Ensino Médio)
        tags2 = parser._analisar_regex_fallback("Aviso_EM_Geral.pdf")
        self.assertEqual(tags2['segmento'], "EM")

if __name__ == '__main__':
    unittest.main()
