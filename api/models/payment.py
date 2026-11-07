from datetime import datetime
import uuid
from typing import List, Optional
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from pydantic import BaseModel, Field, ConfigDict
from api.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(String(64), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    paypal_order_id = Column(String(128), nullable=True, index=True)
    paypal_capture_id = Column(String(128), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    payment_status = Column(String(32), default="pending")  # pending, completed, failed, simulated_completed
    provider = Column(String(32), default="paypal_sandbox")  # paypal_sandbox, paypal_live, simulated
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic Schemas
class InvoiceLineItem(BaseModel):
    agent_id: str
    agent_name: str
    category: str
    description: str
    unit_price: float
    quantity: int = 1
    total: float


class PaymentSummary(BaseModel):
    task_id: str
    task_title: str
    subtotal: float
    platform_fee: float = 0.0
    total_amount: float
    currency: str = "USD"
    items: List[InvoiceLineItem]
    is_budget_exceeded: bool = False
    budget: float
    deliverable_classification: Optional[str] = None
    factual_verification_status: Optional[str] = None


class OrderCreateRequest(BaseModel):
    task_id: str
    return_url: Optional[str] = None
    cancel_url: Optional[str] = None


class OrderCreateResponse(BaseModel):
    order_id: str
    status: str
    amount: float
    currency: str
    provider: str  # paypal_sandbox or simulated
    approval_url: Optional[str] = None


class OrderCaptureRequest(BaseModel):
    task_id: str
    order_id: str


class OrderCaptureResponse(BaseModel):
    success: bool
    transaction_id: str
    capture_id: Optional[str] = None
    order_id: str
    status: str
    amount: float
    currency: str
    provider: str
    message: str


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    task_id: str
    paypal_order_id: Optional[str] = None
    paypal_capture_id: Optional[str] = None
    amount: float
    currency: str
    payment_status: str
    provider: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
