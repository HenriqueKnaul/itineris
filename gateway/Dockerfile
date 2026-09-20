FROM python:3.13-slim

WORKDIR /app

# Instala as dependências primeiro para aproveitar o cache de camadas do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do gateway
COPY . .

EXPOSE 8000

# Comando padrão (o docker-compose sobrescreve para habilitar o --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
