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


def validate_task_payment_eligibility(task: TaskModel, db: Session, action: str = "create payment order") -> None:
    """Positively validates that a task is strictly eligible for payment operations.

    Enforces:
    1. Execution mode must be live_ai (offline scaffolds categorically rejected).
    2. Task status must be awaiting_payment.
    3. All 6 prerequisite workflow steps must be completed.
    4. Quality Assurance audit status must be APPROVED.
    """
    if task.execution_mode != "live_ai":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot {action}: Task was executed in '{task.execution_mode}' mode. Offline scaffolds are strictly ineligible for payment."
        )

    if task.status != "awaiting_payment":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot {action}: Task is in '{task.status}' status. Required state: 'awaiting_payment'."
        )

    steps = db.query(TaskStepModel).filter(TaskStepModel.task_id == task.id).all()
    step_dict = {s.step_name: s for s in steps}
    required_prereqs = ["planning", "research", "data_analysis", "content_generation", "quality_assurance", "finance_calculation"]
    for prereq in required_prereqs:
        if not step_dict.get(prereq) or step_dict[prereq].status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot {action}: Mandatory prerequisite step '{prereq}' is not completed."
            )

    qa_step = step_dict.get("quality_assurance")
    qa_output = json.loads(qa_step.output_data or "{}") if qa_step else {}
    if qa_output.get("audit_status") != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot {action}: Quality Assurance audit status is '{qa_output.get('audit_status')}'. Deliverable must be APPROVED by QA before payment authorization."
        )


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

    # Positive server-side payment eligibility enforcement
    validate_task_payment_eligibility(task, db, action="create payment order")

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

    # Reuse existing active order if in CREATED or APPROVED status to prevent redundant order creation
    existing_tx = db.query(TransactionModel).filter(
        TransactionModel.task_id == task.id,
        TransactionModel.payment_status == "pending"
    ).first()

    if existing_tx and existing_tx.paypal_order_id and not existing_tx.paypal_order_id.startswith("SIM-"):
        try:
            existing_order = await paypal_service.get_order(existing_tx.paypal_order_id)
            status = existing_order.get("status")
            if status in ["CREATED", "APPROVED"]:
                approval_link = next(
                    (l["href"] for l in existing_order.get("links", []) if l.get("rel") == "approve"),
                    f"https://www.sandbox.paypal.com/checkoutnow?token={existing_tx.paypal_order_id}"
                )
                return OrderCreateResponse(
                    order_id=existing_tx.paypal_order_id,
                    status=status,
                    amount=amount,
                    currency="USD",
                    provider=existing_tx.provider,
                    approval_url=approval_link
                )
        except Exception as e:
            logger.warning(f"Could not verify existing order {existing_tx.paypal_order_id}: {e}")

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

    provider = order_result.get("provider", "paypal_sandbox")

    if existing_tx:
        existing_tx.paypal_order_id = order_result["order_id"]
        existing_tx.amount = amount
        existing_tx.provider = provider
    else:
        new_tx = TransactionModel(
            user_id=user_id,
            task_id=task.id,
            paypal_order_id=order_result["order_id"],
            amount=amount,
            currency="USD",
            payment_status="pending",
            provider=provider
        )
        db.add(new_tx)

    log_activity(
        db, task.id, "payment",
        f"PayPal order created ({provider}): {order_result['order_id']} for ${amount:.2f} USD.",
        agent_id="agent_payment_06"
    )
    db.commit()

    return OrderCreateResponse(
        order_id=order_result["order_id"],
        status=order_result["status"],
        amount=amount,
        currency="USD",
        provider=provider,
        approval_url=order_result.get("approval_url")
    )


@router.get("/paypal/order/{order_id}")
async def get_paypal_order_status(order_id: str, db: Session = Depends(get_db)):
    """Retrieves live verification status of a PayPal order directly from PayPal Orders v2 API."""
    try:
        order = await paypal_service.get_order(order_id)
        return {
            "order_id": order_id,
            "status": order.get("status"),
            "intent": order.get("intent"),
            "amount": order.get("purchase_units", [{}])[0].get("amount"),
            "payee": order.get("purchase_units", [{}])[0].get("payee")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to retrieve order: {str(e)}")


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

    # 1. Prevent duplicate captures (Idempotency Guard preserves historical successful captures)
    if tx and tx.payment_status in ["completed", "simulated_completed"]:
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

    # 2. Shared Positive Server-Side Payment Eligibility Enforcement
    validate_task_payment_eligibility(task, db, action="capture payment")

    expected_amount = task.total_cost or 8.00

    # 2. Retrieve live order directly from PayPal to verify APPROVED state before capturing
    if not payload.order_id.startswith("SIM-") and paypal_service.is_configured:
        try:
            live_order = await paypal_service.get_order(payload.order_id)
            live_status = live_order.get("status")

            if live_status == "COMPLETED":
                # Already captured on PayPal
                if tx:
                    tx.payment_status = "completed"
                    db.commit()
                task.status = "paid"
                db.commit()
                return OrderCaptureResponse(
                    success=True,
                    transaction_id=tx.id if tx else "tx_already_completed",
                    capture_id=tx.paypal_capture_id if tx else "cap_completed",
                    order_id=payload.order_id,
                    status="COMPLETED",
                    amount=expected_amount,
                    currency="USD",
                    provider="paypal_sandbox",
                    message="Order is already captured and completed."
                )

            if live_status != "APPROVED":
                logger.warning(f"Capture attempt rejected: Order {payload.order_id} is in status '{live_status}', not 'APPROVED'.")
                raise HTTPException(
                    status_code=400,
                    detail=f"Capture failed: Order status on PayPal is '{live_status}'. The buyer must log in to PayPal and approve the payment first."
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error checking order status on PayPal: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to verify order approval on PayPal: {str(e)}")

    # 3. Execute Capture strictly on approved orders
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

    # Advance workflow to final delivery automatically if prior steps are completed
    try:
        step_delivery = db.query(TaskStepModel).filter(
            TaskStepModel.task_id == task.id,
            TaskStepModel.step_name == "final_delivery"
        ).first()
        if step_delivery and step_delivery.status == "pending":
            await orchestration_engine.advance_task(db, task.id)
    except Exception as e:
        logger.error(f"Error auto-advancing deliverable post-payment: {e}")
        task.status = "paid"
        db.commit()

    log_activity(
        db, task.id, "payment",
        f"PayPal payment captured successfully: {capture_res.get('capture_id')} for ${capture_res['amount']:.2f} USD.",
        agent_id="agent_payment_06"
    )
    db.commit()

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
