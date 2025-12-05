"""
Módulo de Logging Centralizado.

Substitui o uso de 'print' por logs estruturados, essenciais para
monitoramento em ambientes Cloud (Google Cloud Logging).
"""

import logging
import sys

def get_logger(name: str) -> logging.Logger:
    """
    Configura e retorna uma instância de logger com formatação padronizada.

    Args:
        name (str): O nome do módulo que está chamando o log (geralmente __name__).

    Returns:
        logging.Logger: Instância configurada do logger.
    """
    logger = logging.getLogger(name)
    
    # Evita adicionar múltiplos handlers se o logger já estiver configurado
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Formatter: Inclui data, nível, módulo e mensagem
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        )

        # StreamHandler: Envia logs para stdout (padrão para containers/Docker)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)

    return logger