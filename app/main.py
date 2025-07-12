from contextlib import asynccontextmanager
import uvicorn
from app.routes.middleware import add_middleware
from app.routes import payments
from app.core.config import settings
from app.core.database import init_db
from app.services.core.queue import QueueManager
from fastapi import FastAPI

# Global queue manager
queue_manager = QueueManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento do ciclo de vida da aplicação"""
    # Inicializa banco de dados
    await init_db()
    
    # Inicia queue manager
    await queue_manager.start()
    
    yield
    
    # Cleanup
    await queue_manager.stop()


# Aplicação FastAPI
app = FastAPI(
    title="Rinha de Backend 2025",
    description="Payment processing system for Rinha de Backend 2025",
    version="1.0.0",
    lifespan=lifespan,
)

# Adiciona middleware
add_middleware(app)

# Inclui rotas dos endpoints obrigatórios
app.include_router(payments.router, tags=["payments"])

# Disponibiliza queue manager via dependency injection
app.state.queue_manager = queue_manager


def main():
    """Executa na porta 9999"""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,  # Porta 9999
        workers=1,
        loop="uvloop",
        access_log=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
