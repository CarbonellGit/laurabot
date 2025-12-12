"""
Módulo Central de Extensões.
Evita importações circulares centralizando as instâncias das extensões.
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from authlib.integrations.flask_client import OAuth

# 1. Limiter (Rate Limiting)
limiter = Limiter(
    key_func=get_remote_address,
    # Em produção, idealmente usar Redis. Para dev/demo, memória é ok.
    storage_uri="memory://",
    default_limits=["200 per day", "50 per hour"]
)

# 2. CSRF Protection
csrf = CSRFProtect()

# 3. OAuth (Authlib)
oauth = OAuth()
