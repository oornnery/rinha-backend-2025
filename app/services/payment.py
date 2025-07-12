import time
from typing import Any, Dict

import httpx

from app.core.config import settings
from app.models.payment import Payment

from app.services.core.circuit import CircuitBreaker


class PaymentProcessor:
    """Intermediação para 2 processadores com resiliência"""

    def __init__(self):
        self.processors = {
            0: {
                "url": f"{settings.payment_0_url}/payments",
                "health_url": f"{settings.payment_0_url}/health",
                "circuit_breaker": CircuitBreaker(
                    failure_threshold=3, timeout_seconds=30, name="processor_1"
                ),
                "fee": 0.02,  # 2%
                "max_concurrent": 15,
                "current_load": 0,
                "priority": 1,
            },
            1: {
                "url": f"{settings.payment_1_url}/payments",
                "health_url": f"{settings.payment_1_url}/health",
                "circuit_breaker": CircuitBreaker(
                    failure_threshold=5, timeout_seconds=60, name="processor_2"
                ),
                "fee": 0.025,  # 2.5%
                "max_concurrent": 20,
                "current_load": 0,
                "priority": 2,
            },
        }

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.request_timeout),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )

        # Cache de health check (máximo 1 vez a cada 5 segundos)
        self.health_cache = {}
        self.last_health_check = {}

    async def get_optimal_processor(self) -> int:
        """Seleciona o melhor processador disponível"""
        current_time = time.time()
        available_processors = []

        for processor_id, config in self.processors.items():
            # Verifica circuit breaker
            if not config["circuit_breaker"].is_healthy:
                continue

            # Verifica carga atual
            if config["current_load"] >= config["max_concurrent"]:
                continue

            # Health check limitado a 1 vez a cada 5 segundos
            if (
                processor_id not in self.last_health_check
                or current_time - self.last_health_check[processor_id]
                > settings.health_check_interval
            ):
                health_status = await self._check_health(processor_id)
                self.health_cache[processor_id] = health_status
                self.last_health_check[processor_id] = current_time

            if self.health_cache.get(processor_id, {}).get("healthy", False):
                available_processors.append(
                    (processor_id, config["priority"], config["fee"])
                )

        if not available_processors:
            # Fallback para processador com menor carga
            return min(
                self.processors.keys(),
                key=lambda x: self.processors[x]["current_load"],
            )

        # Prioriza menor taxa (processador mais barato)
        available_processors.sort(key=lambda x: (x[1], x[2]))
        return available_processors[0][0]

    async def process_payment(self, payment: Payment) -> Dict[str, Any]:
        """Processa pagamento com processador selecionado"""
        processor_id = await self.get_optimal_processor()
        processor_config = self.processors[processor_id]

        payment_data = {
            "amount": payment.amount,
            "currency": payment.currency,
            "external_id": str(payment.id),
        }

        # Incrementa contador de carga
        processor_config["current_load"] += 1

        try:
            response = await processor_config["circuit_breaker"].call(
                self._make_payment_request,
                processor_config["url"],
                payment_data,
            )

            return {
                "success": True,
                "processor_id": processor_id,
                "external_id": response.get("id"),
                "fee": payment.amount * processor_config["fee"],
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "processor_id": processor_id,
            }
        finally:
            # Decrementa contador de carga
            processor_config["current_load"] -= 1

    async def _make_payment_request(
        self, url: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Faz requisição HTTP para o processador"""
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()

    async def _check_health(self, processor_id: int) -> Dict[str, Any]:
        """Verifica saúde do processador"""
        try:
            config = self.processors[processor_id]
            response = await self.client.get(config["health_url"], timeout=2.0)
            response.raise_for_status()
            return {"healthy": True}
        except Exception:
            return {"healthy": False}

    def get_processor_stats(self) -> Dict[str, Any]:
        """Estatísticas para payment-summary"""
        return {
            0: {
                "current_load": self.processors[0]["current_load"],
                "healthy": self.health_cache.get(0, {}).get("healthy", False),
            },
            1: {
                "current_load": self.processors[1]["current_load"],
                "healthy": self.health_cache.get(1, {}).get("healthy", False),
            },
        }

    async def close(self) -> None:
        """Fecha cliente HTTP"""
        await self.client.aclose()
