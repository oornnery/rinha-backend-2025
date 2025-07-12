import time
from typing import Callable
from fastapi import FastAPI, Request


def add_middleware(app: FastAPI):
    """Adiciona middleware para performance"""
    
    @app.middleware("http")
    async def performance_middleware(request: Request, call_next: Callable):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
