import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.task import TaskModel, TaskStepModel
from api.models.payment import (
    TransactionModel,
    PaymentSummary,
    OrderCreateRequest,
    OrderCreateResponse,
    OrderCaptureRequest,
    OrderCaptureResponse,
    TransactionResponse,
)
from api.services.paypal_service import paypal_service
from api.services.agents.finance_agent import FinanceAgent
from api.services.orchestrator import orchestration_engine, log_activity

logger = logging.getLogger(__name__)
finance_agent = FinanceAgent()

router = APIRouter(prefix="/api/payments", tags=["Payments"])


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    return "user_guest_01"


@router.get("/summary/{task_id}", response_model=PaymentSummary)
def get_payment_summary(task_id: str, db: Session = Depends(get_db)):
    """Computes transparent invoice breakdown using trusted database records."""
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    assigned_agents = ["agent_research_01", "agent_analysis_02", "agent_content_03", "agent_qa_04"]
    invoice = finance_agent.calculate_invoice(
        task_id=task.id,
        task_title=task.title,
        budget=task.budget,
        assigned_agent_ids=assigned_agents,
        db=db
    )
    return invoice


@router.post("/paypal/create-order", response_model=OrderCreateResponse)
async def create_paypal_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Creates a PayPal order via Orders v2 API based on backend database calculations."""
    task = db.query(TaskModel).filter(TaskModel.id == payload.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    # Calculate exact invoice from DB records - NEVER trust amounts from the frontend
    assigned_agents = ["agent_research_01", "agent_analysis_02", "agent_content_03", "agent_qa_04"]
    invoice = finance_agent.calculate_invoice(
        task_id=task.id,
        task_title=task.title,
        budget=task.budget,
        assigned_agent_ids=assigned_agents,
        db=db
    )

    amount = invoice.total_amount
    task.total_cost = amount
    db.commit()

    order_result = await paypal_service.create_order(
        task_id=task.id,
        task_title=task.title,
        amount=amount,
        currency="USD",
        items=invoice.items,
        return_url=payload.return_url,
        cancel_url=payload.cancel_url
    )

    # Persist or update transaction record
    existing_tx = db.query(TransactionModel).filter(
        TransactionModel.task_id == task.id,
        TransactionModel.payment_status == "pending"
    ).first()

    if existing_tx:
        existing_tx.paypal_order_id = order_result["order_id"]
        existing_tx.amount = amount
        existing_tx.provider = order_result["provider"]
    else:
        new_tx = TransactionModel(
            user_id=user_id,
            task_id=task.id,
            paypal_order_id=order_result["order_id"],
            amount=amount,
            currency="USD",
            payment_status="pending",
            provider=order_result["provider"]
        )
        db.add(new_tx)

    log_activity(
        db, task.id, "payment",
        f"PayPal order created ({order_result['provider']}): {order_result['order_id']} for ${amount:.2f} USD.",
        agent_id="agent_payment_06"
    )
    db.commit()

    return OrderCreateResponse(
        order_id=order_result["order_id"],
        status=order_result["status"],
        amount=amount,
        currency="USD",
        provider=order_result["provider"],
        approval_url=order_result.get("approval_url")
    )


@router.post("/paypal/capture-order", response_model=OrderCaptureResponse)
async def capture_paypal_order(
    payload: OrderCaptureRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Captures and verifies authorized PayPal payment, unlocks deliverables."""
    task = db.query(TaskModel).filter(TaskModel.id == payload.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    tx = db.query(TransactionModel).filter(
        TransactionModel.task_id == task.id,
        TransactionModel.paypal_order_id == payload.order_id
    ).first()

    if tx and tx.payment_status in ["completed", "simulated_completed"]:
        # Idempotent response
        return OrderCaptureResponse(
            success=True,
            transaction_id=tx.id,
            capture_id=tx.paypal_capture_id,
            order_id=payload.order_id,
            status="COMPLETED",
            amount=tx.amount,
            currency=tx.currency,
            provider=tx.provider,
            message="Payment was already captured and verified."
        )

    expected_amount = task.total_cost or 8.00

    capture_res = await paypal_service.capture_order(
        order_id=payload.order_id,
        expected_amount=expected_amount,
        currency="USD"
    )

    if not capture_res["success"]:
        raise HTTPException(status_code=400, detail=f"Capture failed: {capture_res['message']}")

    final_status = "completed" if capture_res["provider"].startswith("paypal") else "simulated_completed"

    if tx:
        tx.paypal_capture_id = capture_res["capture_id"]
        tx.payment_status = final_status
        tx.amount = capture_res["amount"]
    else:
        tx = TransactionModel(
            user_id=user_id,
            task_id=task.id,
            paypal_order_id=payload.order_id,
            paypal_capture_id=capture_res["capture_id"],
            amount=capture_res["amount"],
            currency=capture_res["currency"],
            payment_status=final_status,
            provider=capture_res["provider"]
        )
        db.add(tx)

    task.status = "paid"
    db.commit()

    # Advance workflow to final delivery automatically!
    try:
        await orchestration_engine.advance_task(db, task.id)
        # Advance again to execute final_delivery node
        await orchestration_engine.advance_task(db, task.id)
    except Exception as e:
        logger.error(f"Error auto-advancing deliverable post-payment: {e}")

    return OrderCaptureResponse(
        success=True,
        transaction_id=tx.id,
        capture_id=capture_res["capture_id"],
        order_id=payload.order_id,
        status="COMPLETED",
        amount=capture_res["amount"],
        currency=capture_res["currency"],
        provider=capture_res["provider"],
        message="Payment authorized and captured. Final deliverable unlocked."
    )


@router.get("/transactions", response_model=List[TransactionResponse])
def list_transactions(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """Lists past payment transactions for audit and accounting."""
    txs = (
        db.query(TransactionModel)
        .filter(TransactionModel.user_id == user_id)
        .order_by(TransactionModel.created_at.desc())
        .all()
    )
    return txs
