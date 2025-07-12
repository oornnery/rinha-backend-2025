from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float = Field(gt=0)
    currency: str = Field(default="BRL", max_length=3)
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, index=True)
    processor_id: Optional[int] = Field(default=None, index=True)
    attempts: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=datetime.now(timezone.utc))
    external_id: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    fee: Optional[float] = Field(default=None, ge=0)


class PaymentCreate(SQLModel):
    amount: float = Field(gt=0)
    currency: str = Field(default="BRL", max_length=3)


class PaymentResponse(SQLModel):
    id: int
    amount: float
    currency: str
    status: PaymentStatus
    processor_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PurgeResponse(SQLModel):
    message: str
    deleted_count: int


# OBRIGATÓRIO: Schema para payment-summary
class PaymentSummaryResponse(SQLModel):
    processor_1: dict
    processor_2: dict
    total_payments: int
    total_amount: float
