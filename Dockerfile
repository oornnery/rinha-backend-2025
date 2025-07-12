# 1. Use a imagem oficial do Python como imagem base
FROM python:3.13-slim

# 2. Defina o diretório de trabalho no contêiner
WORKDIR /app

# 3. Instale o uv
RUN pip install uv

# 4. Copie os arquivos de dependência
COPY pyproject.toml uv.lock ./

# 5. Instale as dependências do projeto
RUN uv sync

# 6. Copie o código da aplicação
COPY ./app ./app

# 7. Exponha a porta em que a aplicação será executada
EXPOSE 9999

# 8. Defina o comando para executar a aplicação
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9999"]
