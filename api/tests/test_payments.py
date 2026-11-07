import json
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.database import SessionLocal
from api.models.task import TaskModel, TaskStepModel
from api.services.paypal_service import paypal_service

client = TestClient(app)


def test_payment_lifecycle():
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
