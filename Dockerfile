# Usa uma imagem Python leve e oficial
FROM python:3.10-slim

# Define variáveis de ambiente para otimizar o Python
# PYTHONDONTWRITEBYTECODE: Evita criar arquivos .pyc
# PYTHONUNBUFFERED: Garante que os logs apareçam imediatamente no console do GCP
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema necessárias (se houver)
# Para pypdf e ferramentas básicas, as libs padrão costumam bastar, 
# mas mantemos o apt-get limpo para garantir uma imagem pequena.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia apenas o requirements.txt primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências Python
# Adicionamos gunicorn explicitamente aqui para não precisar editar seu txt
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

# Copia todo o código restante para o container
COPY . .

# Expõe a porta que o Cloud Run espera (padrão 8080)
ENV PORT=8080

# Comando de inicialização usando Gunicorn
# -w 2: Define 2 workers (ajustável conforme necessidade)
# --threads 8: Suporte a threads (importante para o seu processamento background e streaming)
# --timeout 0: Remove timeout do gunicorn para deixar o Cloud Run gerenciar
# run:app : Aponta para o arquivo run.py (embora o ideal fosse src:create_app(), o run.py importa o app)
# Mas melhor: vamos apontar direto para a factory para ser mais robusto: "src:create_app()"
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 "src:create_app()"