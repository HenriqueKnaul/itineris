FROM python:3.11-slim

WORKDIR /app

# Copia e instala as dependências
COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt

# Copia todo o código da aplicação
COPY ./app ./app

# Expõe a porta do auth-service
EXPOSE 5000

# Comando para rodar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]