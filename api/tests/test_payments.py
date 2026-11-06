import pytest
from fastapi.testclient import TestClient
from api.main import app

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

    # 3. Create PayPal order
    order_res = client.post("/api/payments/paypal/create-order", json={"task_id": task_id})
    assert order_res.status_code == 200
    order_data = order_res.json()
    assert "order_id" in order_data
    assert order_data["amount"] == 8.00
    order_id = order_data["order_id"]

    # 4. If live order, unapproved capture returns HTTP 400 with ORDER_NOT_APPROVED;
    # then simulate capture to verify ledger persistence and deliverable unlocking.
    cap_res = client.post("/api/payments/paypal/capture-order", json={
        "task_id": task_id,
        "order_id": order_id
    })
    
    if cap_res.status_code == 400:
        # Expected for live PayPal Sandbox order before human buyer approval
        assert "Capture failed" in cap_res.json()["detail"]
        # Now test capture lifecycle using test simulated order ID
        sim_order_id = f"SIM-ORD-{task_id[:8]}"
        cap_res = client.post("/api/payments/paypal/capture-order", json={
            "task_id": task_id,
            "order_id": sim_order_id
        })
        order_id = sim_order_id

    assert cap_res.status_code == 200
    cap_data = cap_res.json()
    assert cap_data["success"] is True
    assert cap_data["status"] == "COMPLETED"

    # 5. Test idempotency (duplicate capture should be safe and return already captured)
    dup_res = client.post("/api/payments/paypal/capture-order", json={
        "task_id": task_id,
        "order_id": order_id
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
