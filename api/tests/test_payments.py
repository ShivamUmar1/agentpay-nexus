import os
import sys

# Ensure test environment settings are active before importing application components
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("GUEST_SESSION_SECRET", "test-secret-key-32-chars-minimum-long-secure")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_agentpay.db")

import json
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.config import settings
from api.database import SessionLocal
from api.models.task import TaskModel, TaskStepModel
from api.models.payment import TransactionModel
from api.services.paypal_service import paypal_service

client = TestClient(app)


def test_payment_lifecycle():
    """Preserved baseline test verifying standard lifecycle and simulated demo fallback."""
    # 1. Create a task
    task_res = client.post("/api/tasks", json={
        "title": "Fintech AI Agent Market Research",
        "description": "Analyze agentic payment workflows and marketplace economics.",
        "budget": 15.0,
        "currency": "USD"
    })
    assert task_res.status_code == 200
    task_id = task_res.json()["id"]

    # 2. Get payment summary
    sum_res = client.get(f"/api/payments/summary/{task_id}")
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["total_amount"] == 8.00  # $2 + $3 + $2 + $1
    assert summary["is_budget_exceeded"] is False
    assert len(summary["items"]) == 4

    # Prepare task state in database: simulate completion of all 6 prerequisite steps
    # with genuine QA approval in live_ai execution mode.
    db = SessionLocal()
    try:
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        task.status = "awaiting_payment"
        task.current_step = "payment_approval"
        task.execution_plan = json.dumps({"execution_mode": "live_ai"})

        steps = db.query(TaskStepModel).filter(TaskStepModel.task_id == task_id).all()
        for s in steps:
            s.status = "completed"
            if s.step_name == "quality_assurance":
                s.output_data = json.dumps({
                    "audit_status": "APPROVED",
                    "completeness_score": 95,
                    "factual_coherence_score": 95,
                    "constraint_compliance": True,
                    "budget_compliance": True,
                    "feedback": "All requirements verified.",
                    "corrections_required": False
                })
        db.commit()
    finally:
        db.close()

    # 3. Create PayPal order (mocked to prevent live sandbox order pollution during automated test)
    mock_order = {
        "order_id": f"TEST-ORD-{task_id[:8]}",
        "status": "CREATED",
        "approval_url": f"https://www.sandbox.paypal.com/checkoutnow?token=TEST-ORD-{task_id[:8]}"
    }
    with patch.object(paypal_service, "create_order", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_order
        order_res = client.post("/api/payments/paypal/create-order", json={"task_id": task_id})
        assert order_res.status_code == 200
        order_data = order_res.json()
        assert "order_id" in order_data
        assert order_data["amount"] == 8.00

    # 4. Simulate capture using built-in test order to verify ledger persistence and deliverable unlocking
    sim_order_id = f"SIM-ORD-{task_id[:8]}"
    cap_res = client.post("/api/payments/paypal/capture-order", json={
        "task_id": task_id,
        "order_id": sim_order_id
    })
    assert cap_res.status_code == 200
    cap_data = cap_res.json()
    assert cap_data["success"] is True
    assert cap_data["status"] == "COMPLETED"

    # 5. Test idempotency (duplicate capture should be safe and return already captured)
    dup_res = client.post("/api/payments/paypal/capture-order", json={
        "task_id": task_id,
        "order_id": sim_order_id
    })
    assert dup_res.status_code == 200
    dup_data = dup_res.json()
    assert dup_data["success"] is True

    # 6. Verify task status updated
    updated_task = client.get(f"/api/tasks/{task_id}").json()
    assert updated_task["status"] in ["paid", "completed"]

    # 7. Check transactions list
    tx_res = client.get("/api/payments/transactions")
    assert tx_res.status_code == 200
    txs = tx_res.json()
    assert len(txs) >= 1


# ---------------------------------------------------------------------------
# MOCKED REGRESSION TESTS: REAL PAYPAL CAPTURE RESPONSE VALIDATION
# ---------------------------------------------------------------------------

def make_paypal_capture_response(
    status="COMPLETED",
    capture_id="CAP-12345678",
    capture_status="COMPLETED",
    amount="8.00",
    currency="USD",
    include_pu=True,
    include_payments=True,
    include_captures=True,
    include_amount=True,
):
    if not include_pu:
        return {"id": "ORD-12345", "status": status, "purchase_units": []}

    captures = []
    if include_captures:
        capture_item = {
            "status": capture_status,
        }
        if capture_id is not None:
            capture_item["id"] = capture_id
        if include_amount:
            amount_obj = {}
            if amount is not None:
                amount_obj["value"] = amount
            if currency is not None:
                amount_obj["currency_code"] = currency
            capture_item["amount"] = amount_obj
        captures.append(capture_item)

    payments = {}
    if include_payments:
        payments["captures"] = captures

    return {
        "id": "ORD-12345",
        "status": status,
        "purchase_units": [
            {
                "reference_id": "default",
                "payments": payments
            }
        ]
    }


async def run_mocked_capture(payload, expected_amount=8.0, expected_currency="USD"):
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = payload

    with patch.object(paypal_service, "get_access_token", new_callable=AsyncMock) as mock_tok, \
         patch.object(settings, "PAYPAL_CLIENT_ID", "mock_cid"), \
         patch.object(settings, "PAYPAL_CLIENT_SECRET", "mock_secret"), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:

        mock_tok.return_value = "mock_token"
        mock_post.return_value = mock_res

        return await paypal_service.capture_order(
            order_id="REAL-ORD-99999",
            expected_amount=expected_amount,
            currency=expected_currency
        )


@pytest.mark.asyncio
async def test_capture_validation_valid_completed():
    """Scenario 1: Valid COMPLETED capture, USD 8.00, valid capture ID -> Success."""
    res = await run_mocked_capture(make_paypal_capture_response())
    assert res["success"] is True
    assert res["status"] == "COMPLETED"
    assert res["capture_id"] == "CAP-12345678"
    assert res["amount"] == 8.00
    assert res["currency"] == "USD"


@pytest.mark.asyncio
async def test_capture_validation_amount_below_expected():
    """Scenario 2: Captured amount below expected -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(amount="7.99"))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "amount mismatch" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_amount_above_expected():
    """Scenario 3: Captured amount above expected -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(amount="8.01"))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "amount mismatch" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_currency_eur():
    """Scenario 4: Captured currency EUR -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(currency="EUR"))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "currency mismatch" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_currency_inr():
    """Scenario 5: Captured currency INR -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(currency="INR"))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "currency mismatch" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_missing_currency_code():
    """Scenario 6: Missing currency code -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(currency=None))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "missing currency" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_missing_purchase_units():
    """Scenario 7: Missing purchase units -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(include_pu=False))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "missing purchase units" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_missing_captures_array():
    """Scenario 8: Missing captures array -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(include_payments=False))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "missing" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_empty_captures_array():
    """Scenario 9: Empty captures array -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(include_captures=False))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "missing captures array" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_missing_capture_id():
    """Scenario 10: Missing capture ID -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(capture_id=""))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "capture id" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_missing_capture_amount():
    """Scenario 11: Missing capture amount -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(include_amount=False))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "missing amount" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_malformed_captured_amount():
    """Scenario 12: Malformed captured amount -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(amount="abc"))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "malformed" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_non_finite_captured_amount():
    """Scenario 13: Non-finite captured amount -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(amount="NaN"))
    assert res["success"] is False
    assert res["status"] == "FAILED"
    assert "malformed or non-finite" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_capture_record_status_not_completed():
    """Scenario 14: Capture record status not COMPLETED -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(capture_status="PENDING"))
    assert res["success"] is False
    assert res["status"] == "PENDING"
    assert "capture record status" in res["message"].lower()


@pytest.mark.asyncio
async def test_capture_validation_overall_order_status_not_completed():
    """Scenario 15: Overall order status not COMPLETED -> Failure."""
    res = await run_mocked_capture(make_paypal_capture_response(status="APPROVED"))
    assert res["success"] is False
    assert res["status"] == "APPROVED"
    assert "expected 'completed'" in res["message"].lower()


# ---------------------------------------------------------------------------
# ROUTER FAILURE BOUNDARY TESTS
# ---------------------------------------------------------------------------

def _setup_eligible_task_for_capture():
    """Helper to create an eligible task awaiting payment in the test DB with a fresh client session."""
    local_client = TestClient(app)
    task_res = local_client.post("/api/tasks", json={
        "title": "Security Router Boundary Test Task",
        "description": "Validating payment capture failure boundary.",
        "budget": 10.0,
        "currency": "USD"
    })
    assert task_res.status_code == 200
    task_id = task_res.json()["id"]

    db = SessionLocal()
    try:
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        task.status = "awaiting_payment"
        task.current_step = "payment_approval"
        task.total_cost = 8.00
        task.execution_plan = json.dumps({"execution_mode": "live_ai"})

        steps = db.query(TaskStepModel).filter(TaskStepModel.task_id == task_id).all()
        for s in steps:
            s.status = "completed"
            if s.step_name == "content_generation":
                s.output_data = json.dumps({
                    "report_markdown": "CONFIDENTIAL EXECUTIVE DELIVERABLE"
                })
            elif s.step_name == "quality_assurance":
                s.output_data = json.dumps({
                    "audit_status": "APPROVED",
                    "completeness_score": 95,
                    "factual_coherence_score": 100,
                    "constraint_compliance": True,
                    "budget_compliance": True
                })
            elif s.step_name == "payment_approval":
                s.status = "pending"
            elif s.step_name == "final_delivery":
                s.status = "pending"

        # Create pending transaction
        tx = TransactionModel(
            user_id=task.user_id,
            task_id=task.id,
            paypal_order_id="REAL-ORD-ROUTER-TEST",
            amount=8.00,
            currency="USD",
            payment_status="pending",
            provider="paypal_sandbox"
        )
        db.add(tx)
        db.commit()
    finally:
        db.close()

    return local_client, task_id


def test_router_capture_amount_mismatch_fails_and_locks_deliverables():
    """Router test: Amount mismatch returns HTTP 400, task is NOT paid, deliverables remain locked."""
    local_client, task_id = _setup_eligible_task_for_capture()

    # Mock PayPal service: live order is APPROVED, but capture returns amount mismatch failure
    with patch.object(settings, "PAYPAL_CLIENT_ID", "mock_cid"), \
         patch.object(settings, "PAYPAL_CLIENT_SECRET", "mock_sec"), \
         patch.object(paypal_service, "get_order", new_callable=AsyncMock) as mock_get_order, \
         patch.object(paypal_service, "capture_order", new_callable=AsyncMock) as mock_capture:

        mock_get_order.return_value = {"id": "REAL-ORD-ROUTER-TEST", "status": "APPROVED"}
        mock_capture.return_value = {
            "success": False,
            "order_id": "REAL-ORD-ROUTER-TEST",
            "capture_id": "CAP-TAMPERED-01",
            "status": "FAILED",
            "amount": 7.00,
            "currency": "USD",
            "provider": "paypal_sandbox",
            "is_simulated": False,
            "message": "Payment amount mismatch: captured $7.00, expected $8.00."
        }

        cap_res = local_client.post("/api/payments/paypal/capture-order", json={
            "task_id": task_id,
            "order_id": "REAL-ORD-ROUTER-TEST"
        })
        assert cap_res.status_code == 400
        assert "Payment amount mismatch" in cap_res.json()["detail"]

    # Verify task status is NOT paid
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        assert t.status == "awaiting_payment"
        assert t.status != "paid"

        # Verify transaction is NOT completed
        tx = db.query(TransactionModel).filter(TransactionModel.task_id == task_id).first()
        assert tx.payment_status == "pending"
        assert tx.payment_status != "completed"

        # Verify final delivery is NOT advanced
        step_delivery = db.query(TaskStepModel).filter(
            TaskStepModel.task_id == task_id,
            TaskStepModel.step_name == "final_delivery"
        ).first()
        assert step_delivery.status == "pending"
    finally:
        db.close()

    # Verify deliverable remains locked on public task response
    task_view = local_client.get(f"/api/tasks/{task_id}").json()
    assert task_view["status"] == "awaiting_payment"
    content_step = next(s for s in task_view["steps"] if s["step_name"] == "content_generation")
    assert content_step["output_data"]["is_locked"] is True
    assert "PROTECTED DELIVERABLE" in content_step["output_data"]["report_markdown"]


def test_router_capture_currency_mismatch_fails_and_locks_deliverables():
    """Router test: Currency mismatch returns HTTP 400, task is NOT paid, deliverables remain locked."""
    local_client, task_id = _setup_eligible_task_for_capture()

    with patch.object(settings, "PAYPAL_CLIENT_ID", "mock_cid"), \
         patch.object(settings, "PAYPAL_CLIENT_SECRET", "mock_sec"), \
         patch.object(paypal_service, "get_order", new_callable=AsyncMock) as mock_get_order, \
         patch.object(paypal_service, "capture_order", new_callable=AsyncMock) as mock_capture:

        mock_get_order.return_value = {"id": "REAL-ORD-ROUTER-TEST", "status": "APPROVED"}
        mock_capture.return_value = {
            "success": False,
            "order_id": "REAL-ORD-ROUTER-TEST",
            "capture_id": "CAP-TAMPERED-02",
            "status": "FAILED",
            "amount": 8.00,
            "currency": "EUR",
            "provider": "paypal_sandbox",
            "is_simulated": False,
            "message": "Payment currency mismatch: captured EUR, expected USD."
        }

        cap_res = local_client.post("/api/payments/paypal/capture-order", json={
            "task_id": task_id,
            "order_id": "REAL-ORD-ROUTER-TEST"
        })
        assert cap_res.status_code == 400
        assert "Payment currency mismatch" in cap_res.json()["detail"]

    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        assert t.status == "awaiting_payment"
        tx = db.query(TransactionModel).filter(TransactionModel.task_id == task_id).first()
        assert tx.payment_status == "pending"
    finally:
        db.close()


def test_router_capture_missing_capture_id_fails_and_locks_deliverables():
    """Router test: Missing capture ID returns HTTP 400, task is NOT paid, deliverables remain locked."""
    local_client, task_id = _setup_eligible_task_for_capture()

    with patch.object(settings, "PAYPAL_CLIENT_ID", "mock_cid"), \
         patch.object(settings, "PAYPAL_CLIENT_SECRET", "mock_sec"), \
         patch.object(paypal_service, "get_order", new_callable=AsyncMock) as mock_get_order, \
         patch.object(paypal_service, "capture_order", new_callable=AsyncMock) as mock_capture:

        mock_get_order.return_value = {"id": "REAL-ORD-ROUTER-TEST", "status": "APPROVED"}
        mock_capture.return_value = {
            "success": False,
            "order_id": "REAL-ORD-ROUTER-TEST",
            "capture_id": None,
            "status": "FAILED",
            "amount": 0.0,
            "currency": "USD",
            "provider": "paypal_sandbox",
            "is_simulated": False,
            "message": "Payment verification failed: Missing or empty capture ID."
        }

        cap_res = local_client.post("/api/payments/paypal/capture-order", json={
            "task_id": task_id,
            "order_id": "REAL-ORD-ROUTER-TEST"
        })
        assert cap_res.status_code == 400
        assert "Missing or empty capture ID" in cap_res.json()["detail"]

    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        assert t.status == "awaiting_payment"
    finally:
        db.close()


def test_router_capture_order_status_not_approved_fails():
    """Router test: Order on PayPal is CREATED (not approved by buyer) -> Rejected with 400."""
    local_client, task_id = _setup_eligible_task_for_capture()

    with patch.object(settings, "PAYPAL_CLIENT_ID", "mock_cid"), \
         patch.object(settings, "PAYPAL_CLIENT_SECRET", "mock_sec"), \
         patch.object(paypal_service, "get_order", new_callable=AsyncMock) as mock_get_order:

        mock_get_order.return_value = {"id": "REAL-ORD-ROUTER-TEST", "status": "CREATED"}

        cap_res = local_client.post("/api/payments/paypal/capture-order", json={
            "task_id": task_id,
            "order_id": "REAL-ORD-ROUTER-TEST"
        })
        assert cap_res.status_code == 400
        assert "The buyer must log in to PayPal and approve the payment first" in cap_res.json()["detail"]

    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        assert t.status == "awaiting_payment"
    finally:
        db.close()
