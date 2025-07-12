FROM python:3.13-slim

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instala uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Define diretório de trabalho
WORKDIR /app

# Copia arquivos de dependências
COPY pyproject.toml uv.lock ./

# Instala dependências
RUN uv sync --frozen --no-dev

# Copia código da aplicação
COPY . .

# Cria usuário não-root
RUN groupadd -r app && useradd -r -g app app
RUN chown -R app:app /app
USER app

# OBRIGATÓRIO: Expõe porta 9999
EXPOSE 9999

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9999/api/health || exit 1

# Executa aplicação
CMD ["uv", "run", "python", "-m", "app.main"]
