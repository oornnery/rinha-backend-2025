import asyncio
import time
from datetime import datetime
from typing import Any, Dict

from sqlmodel import select

from app.core.config import settings
from app.core.database import async_session
from app.models.payment import Payment, PaymentStatus

from ..payment import PaymentProcessor
from fastapi import Request

class QueueManager:
    """Processamento assíncrono para máxima performance"""
    
    def __init__(self):
        self.queue = asyncio.Queue()
        self.max_workers = settings.max_workers
        self.workers = []
        self.processor = PaymentProcessor()
        self.running = False
        
        # Estatísticas para payment-summary
        self.stats = {
            "processed": 0,
            "failed": 0,
            "start_time": time.time(),
        }
        
    async def start(self) -> None:
        """Inicia workers da queue"""
        self.running = True
        
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
    
    async def stop(self) -> None:
        """Para todos os workers"""
        self.running = False
        
        for worker in self.workers:
            worker.cancel()
        
        await asyncio.gather(*self.workers, return_exceptions=True)
        await self.processor.close()
    
    async def enqueue_payment(self, payment_id: int) -> None:
        """Enfileira pagamento para processamento"""
        await self.queue.put({"payment_id": payment_id})
    
    async def _worker(self, worker_name: str) -> None:
        """Worker que processa pagamentos da queue"""
        while self.running:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._process_payment_task(task)
                self.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Worker {worker_name} error: {e}")
    
    async def _process_payment_task(self, task: Dict[str, Any]) -> None:
        """Processa pagamento individual"""
        payment_id = task["payment_id"]
        
        try:
            async with async_session() as session:
                # Busca pagamento
                result = await session.execute(
                    select(Payment).where(Payment.id == payment_id)
                )
                payment = result.scalar_one_or_none()
                
                if not payment:
                    return
                
                # Atualiza status para processando
                payment.status = PaymentStatus.PROCESSING
                payment.attempts += 1
                payment.updated_at = datetime.utcnow()
                
                session.add(payment)
                await session.commit()
                
                # Processa pagamento
                result = await self.processor.process_payment(payment)
                
                if result["success"]:
                    payment.status = PaymentStatus.COMPLETED
                    payment.external_id = result["external_id"]
                    payment.processor_id = result["processor_id"]
                    payment.fee = result["fee"]
                    self.stats["processed"] += 1
                else:
                    payment.error_message = result["error"]
                    
                    # Retry com até 3 tentativas
                    if payment.attempts < 3:
                        payment.status = PaymentStatus.RETRYING
                        
                        # Exponential backoff
                        retry_delay = min(2 ** payment.attempts, 10)
                        await asyncio.sleep(retry_delay)
                        
                        # Re-enfileira
                        await self.enqueue_payment(payment_id)
                    else:
                        payment.status = PaymentStatus.FAILED
                        self.stats["failed"] += 1
                
                payment.updated_at = datetime.utcnow()
                session.add(payment)
                await session.commit()
                
        except Exception as e:
            print(f"Error processing payment {payment_id}: {e}")
            self.stats["failed"] += 1


async def get_queue_manager(request: Request) -> QueueManager:
    """Obtém queue manager do estado da aplicação"""
    return request.app.state.queue_manager
