import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_full_autonomous_agent_workflow():
    # STEP 1: User Request
    task_res = client.post("/api/tasks", json={
        "title": "Electric Vehicle Market Research Report India",
        "description": "Create a detailed market research report about the electric vehicle industry in India. Include market size, major competitors, future trends, opportunities, and a final investment analysis. My maximum budget is $10.",
        "budget": 10.0,
        "currency": "USD"
    })
    assert task_res.status_code == 200
    task_data = task_res.json()
    task_id = task_data["id"]
    assert task_data["status"] == "executing"
    assert task_data["current_step"] == "research"

    # STEP 2: Execute Research Agent
    step1_res = client.post(f"/api/tasks/{task_id}/advance")
    assert step1_res.status_code == 200
    assert step1_res.json()["advanced_step"] == "research"

    # STEP 3: Execute Data Analysis Agent (with deterministic CAGR & chart metrics)
    step2_res = client.post(f"/api/tasks/{task_id}/advance")
    assert step2_res.status_code == 200
    assert step2_res.json()["advanced_step"] == "data_analysis"

    # STEP 4: Execute Content Synthesis Agent
    step3_res = client.post(f"/api/tasks/{task_id}/advance")
    assert step3_res.status_code == 200
    assert step3_res.json()["advanced_step"] == "content_generation"

    # STEP 5: Execute Quality Assurance Agent
    step4_res = client.post(f"/api/tasks/{task_id}/advance")
    assert step4_res.status_code == 200
    assert step4_res.json()["advanced_step"] == "quality_assurance"

    # STEP 6: Execute Finance Agent (Calculate invoice from trusted records)
    step5_res = client.post(f"/api/tasks/{task_id}/advance")
    assert step5_res.status_code == 200
    assert step5_res.json()["advanced_step"] == "finance_calculation"

    # Check task is now awaiting payment
    task_await = client.get(f"/api/tasks/{task_id}").json()
    assert task_await["status"] == "awaiting_payment"
    assert task_await["current_step"] == "payment_approval"
    assert task_await["total_cost"] == 8.00  # Within $10 budget!

    # STEP 7: Payment Summary & Authorization
    summary_res = client.get(f"/api/payments/summary/{task_id}")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_amount"] == 8.00
    assert summary["is_budget_exceeded"] is False

    # STEP 8: Create PayPal Order
    order_res = client.post("/api/payments/paypal/create-order", json={"task_id": task_id})
    assert order_res.status_code == 200
    order_data = order_res.json()
    order_id = order_data["order_id"]

    # STEP 9: User Authorizes & Backend Captures Payment
    capture_res = client.post("/api/payments/paypal/capture-order", json={
        "task_id": task_id,
        "order_id": order_id
    })
    assert capture_res.status_code == 200
    cap_data = capture_res.json()
    assert cap_data["success"] is True

    # STEP 10: Final Delivery Verification
    final_task = client.get(f"/api/tasks/{task_id}").json()
    assert final_task["status"] == "completed"
    assert final_task["final_output"] is not None
    assert "report_markdown" in final_task["final_output"]
    assert "Tata Motors" in final_task["final_output"]["report_markdown"]
    assert "CAGR" in final_task["final_output"]["report_markdown"]

    # STEP 11: Verify Progress & Activity Logs
    activity_res = client.get(f"/api/tasks/{task_id}/activity")
    assert activity_res.status_code == 200
    logs = activity_res.json()
    assert len(logs) >= 6

    # Verify Results endpoint
    results_res = client.get(f"/api/tasks/{task_id}/results")
    assert results_res.status_code == 200
    assert results_res.json()["is_unlocked"] is True
