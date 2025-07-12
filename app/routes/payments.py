from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.database import get_session
from app.models.payment import (
    Payment,
    PaymentCreate,
    PaymentResponse,
    PaymentStatus,
    PaymentSummaryResponse,
    PurgeResponse,
)
from app.services.core.queue import get_queue_manager, QueueManager

router = APIRouter()


@router.post("/payments", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    session: AsyncSession = Depends(get_session),
    queue_manager: QueueManager = Depends(get_queue_manager),
):
    """Endpoint principal para receber pagamentos"""
    try:
        # Cria pagamento
        payment = Payment(
            amount=payment_data.amount,
            currency=payment_data.currency,
            status=PaymentStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        session.add(payment)
        await session.commit()
        await session.refresh(payment)

        # Enfileira para processamento assíncrono
        await queue_manager.enqueue_payment(payment.id)

        return PaymentResponse.from_orm(payment)

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/purge-payments", response_model=PurgeResponse)
async def purge_payments(
    session: AsyncSession = Depends(get_session),
):
    """Endpoint secreto para limpeza (usado pelos testes)"""
    try:
        # Conta pagamentos existentes
        count_result = await session.execute(select(func.count(Payment.id)))
        deleted_count = count_result.scalar()

        # Deleta todos os pagamentos
        await session.execute("DELETE FROM payments")
        await session.commit()

        return PurgeResponse(
            message=f"Successfully purged {deleted_count} payments",
            deleted_count=deleted_count,
        )

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/payment-summary", response_model=PaymentSummaryResponse)
async def payment_summary(
    session: AsyncSession = Depends(get_session),
):
    """Resumo dos pagamentos por processador"""
    try:
        # Busca estatísticas por processador
        result = await session.execute(
            select(
                Payment.processor_id,
                func.count(Payment.id).label("count"),
                func.sum(Payment.amount).label("total_amount"),
            )
            .where(Payment.status == PaymentStatus.COMPLETED)
            .group_by(Payment.processor_id)
        )

        # Inicializa contadores
        processor_stats = {
            1: {"count": 0, "total_amount": 0.0},
            2: {"count": 0, "total_amount": 0.0},
        }

        # Preenche estatísticas
        total_payments = 0
        total_amount = 0.0

        for row in result:
            if row.processor_id in [1, 2]:
                processor_stats[row.processor_id] = {
                    "count": row.count,
                    "total_amount": float(row.total_amount or 0),
                }
                total_payments += row.count
                total_amount += float(row.total_amount or 0)

        return PaymentSummaryResponse(
            processor_1=processor_stats[1],
            processor_2=processor_stats[2],
            total_payments=total_payments,
            total_amount=total_amount,
        )

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
