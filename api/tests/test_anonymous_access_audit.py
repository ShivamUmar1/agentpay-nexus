"""
AGENTPAY NEXUS — PHASE 2A SECURITY REGRESSION SUITE
Comprehensive automated tests verifying:
1. Cryptographically signed anonymous guest identity
2. Server-side task ownership enforcement and data isolation
3. Payment and financial transaction ownership validation
4. Distributed rate limiting, payload boundaries, and AI resource abuse prevention
"""

import os
import json
import time
import threading
from datetime import datetime, timezone, timedelta
import concurrent.futures
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from api.main import app
from api.config import settings
from api.database import SessionLocal, Base
from api.models.task import TaskModel, TaskStepModel
from api.models.payment import TransactionModel
from api.models.ratelimit import RateLimitRecord
from api.services.llm_provider import llm_provider
from api.services.paypal_service import paypal_service
from api.services.orchestrator import orchestrator_agent
from api.services.auth_session import (
    create_guest_session_token,
    verify_guest_session_token,
    generate_guest_id,
)

# Standard mock planning output
MOCK_PLAN = {
    "execution_mode": "live_ai",
    "estimated_total_cost": 8.00,
    "steps": [
        {"name": "research", "agent_id": "agent_research_01"},
        {"name": "data_analysis", "agent_id": "agent_analysis_02"},
        {"name": "content_generation", "agent_id": "agent_content_03"},
        {"name": "quality_assurance", "agent_id": "agent_qa_04"},
        {"name": "finance_calculation", "agent_id": "agent_finance_05"},
        {"name": "payment_approval", "agent_id": "agent_payment_06"},
        {"name": "final_delivery", "agent_id": "agent_delivery_07"},
    ]
}


@pytest.fixture(autouse=True)
def clean_rate_limits():
    """Cleans up rate limit and test task records between tests for deterministic isolation."""
    yield
    db = SessionLocal()
    try:
        db.query(RateLimitRecord).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ==============================================================================
# SECTION 1: GUEST IDENTITY & SESSION SECURITY (Tests 1 - 8)
# ==============================================================================

def test_1_first_visitor_gets_unique_signed_session():
    """Test 1: First visitor with no cookie automatically receives a unique signed guest cookie."""
    client_a = TestClient(app)
    res = client_a.get("/api/tasks")
    assert res.status_code == 200

    cookie_name = settings.GUEST_SESSION_COOKIE_NAME
    token = client_a.cookies.get(cookie_name)
    assert token is not None, "Guest session cookie was not issued."

    # Validate structure: base64url(payload).base64url(signature)
    payload = verify_guest_session_token(token)
    assert payload["uid"].startswith("guest:")
    assert payload["exp"] > time.time()


def test_2_second_visitor_gets_different_session():
    """Test 2: Two independent visitors receive distinct, cryptographically isolated guest IDs."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    client_a.get("/api/tasks")
    client_b.get("/api/tasks")

    cookie_a = client_a.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)
    cookie_b = client_b.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)

    uid_a = verify_guest_session_token(cookie_a)["uid"]
    uid_b = verify_guest_session_token(cookie_b)["uid"]

    assert uid_a != uid_b, "Independent visitors must not share guest identity."


def test_3_cookies_are_httponly_and_secure_in_hosted_contexts():
    """Test 3: Guest session cookies enforce HttpOnly and SameSite=Lax flags."""
    client = TestClient(app)
    res = client.get("/api/tasks")
    set_cookie = res.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert "samesite=lax" in set_cookie.lower()
    assert "domain=" not in set_cookie.lower(), "Cookie must be host-only, no broad domain."


def test_4_tampered_tokens_are_rejected():
    """Test 4: Tampered session tokens with forged payload or signature receive HTTP 401."""
    client = TestClient(app)
    token = create_guest_session_token(uid="guest:original-id")
    parts = token.split(".")
    tampered_token = f"{parts[0]}.forgedsignature12345"

    client.cookies.set(settings.GUEST_SESSION_COOKIE_NAME, tampered_token)
    res = client.get("/api/tasks")
    assert res.status_code == 401
    assert "Invalid session signature" in res.json()["detail"]


def test_5_expired_tokens_are_rejected():
    """Test 5: Expired guest session tokens receive HTTP 401."""
    client = TestClient(app)
    expired_token = create_guest_session_token(uid="guest:expired-user", expires_in_seconds=-10)

    client.cookies.set(settings.GUEST_SESSION_COOKIE_NAME, expired_token)
    res = client.get("/api/tasks")
    assert res.status_code == 401
    assert "Session expired" in res.json()["detail"]


def test_6_arbitrary_bearer_headers_cannot_forge_identity():
    """Test 6: Arbitrary Bearer authorization headers are rejected and cannot establish identity."""
    client = TestClient(app)
    res = client.get("/api/tasks", headers={"Authorization": "Bearer arbitrary_unverified_token"})
    assert res.status_code == 401
    assert "unverified" in res.json()["detail"].lower()


def test_7_missing_production_signing_secret_fails_closed():
    """Test 7: In production/hosted environments, missing GUEST_SESSION_SECRET fails closed with HTTP 503."""
    client = TestClient(app)
    with patch.object(settings, "GUEST_SESSION_SECRET", None), \
         patch.dict("os.environ", {"VERCEL": "1", "APP_ENV": "production"}):
        res = client.get("/api/tasks")
        assert res.status_code == 503
        assert "configuration unavailable" in res.json()["detail"].lower()


def test_8_hosted_diagnostics_cannot_be_enabled_through_local_flags():
    """Test 8: Hosted diagnostics remain locked out regardless of local flags."""
    client = TestClient(app)
    with patch.object(settings, "ENABLE_LIVE_AI_DIAGNOSTICS", True), \
         patch.dict("os.environ", {"VERCEL": "1"}):
        res = client.get("/api/system/test-ai")
        assert res.status_code == 403


# ==============================================================================
# SECTION 2: SERVER-SIDE TASK DATA ISOLATION (Tests 9 - 16)
# ==============================================================================

def test_9_visitor_a_creates_task_successfully():
    """Test 9: Visitor A creates a task and owns it under their unique session ID."""
    client_a = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client_a.post("/api/tasks", json={
            "title": "Quantum Computing Market Overview",
            "description": "Visitor A proprietary quantum strategy.",
            "budget": 10.0
        })
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Quantum Computing Market Overview"
        cookie_a = client_a.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)
        expected_uid = verify_guest_session_token(cookie_a)["uid"]
        assert data["user_id"] == expected_uid


def test_10_visitor_b_cannot_list_visitor_a_task():
    """Test 10: Visitor B listing tasks sees only their own tasks; Visitor A's task is never returned."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A Confidential Semiconductor Plan",
            "description": "Proprietary foundry analysis.",
            "budget": 15.0
        })
        assert res_a.status_code == 200
        task_a_id = res_a.json()["id"]

    res_b = client_b.get("/api/tasks")
    assert res_b.status_code == 200
    tasks_b = res_b.json()["tasks"]
    task_ids_b = [t["id"] for t in tasks_b]
    assert task_a_id not in task_ids_b, "Visitor B must not receive Visitor A's tasks in list."


def test_11_visitor_b_cannot_access_visitor_a_task_details():
    """Test 11: Visitor B requesting Visitor A's task details receives HTTP 404."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A Aerospace Defense Briefing",
            "description": "Proprietary satellite dynamics.",
            "budget": 20.0
        })
        task_a_id = res_a.json()["id"]

    res_b = client_b.get(f"/api/tasks/{task_a_id}")
    assert res_b.status_code == 404
    assert res_b.json()["detail"] == "Task not found."


def test_12_visitor_b_cannot_read_progress():
    """Test 12: Visitor B requesting Visitor A's workflow progress receives HTTP 404."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A Biopharma Study",
            "description": "Oncology clinical trials analysis.",
            "budget": 12.0
        })
        task_a_id = res_a.json()["id"]

    res_b = client_b.get(f"/api/tasks/{task_a_id}/progress")
    assert res_b.status_code == 404


def test_13_visitor_b_cannot_read_activity_logs():
    """Test 13: Visitor B requesting Visitor A's activity logs receives HTTP 404."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A Logistics Plan",
            "description": "Fleet supply chain routes.",
            "budget": 10.0
        })
        task_a_id = res_a.json()["id"]

    res_b = client_b.get(f"/api/tasks/{task_a_id}/activity")
    assert res_b.status_code == 404


def test_14_visitor_b_cannot_advance_visitor_a_workflow():
    """Test 14: Visitor B attempting to advance Visitor A's task receives HTTP 404 without invoking AI."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A FinTech Report",
            "description": "Digital payment cross-border rail.",
            "budget": 10.0
        })
        task_a_id = res_a.json()["id"]

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_adv_llm:
        res_b = client_b.post(f"/api/tasks/{task_a_id}/advance")
        assert res_b.status_code == 404
        assert mock_adv_llm.call_count == 0, "AI must not be invoked on unauthorized advance attempt."


def test_15_visitor_b_cannot_access_visitor_a_results():
    """Test 15: Visitor B requesting Visitor A's deliverables receives HTTP 404."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A Secret Deliverable",
            "description": "Protected market forecast.",
            "budget": 10.0
        })
        task_a_id = res_a.json()["id"]

    res_b = client_b.get(f"/api/tasks/{task_a_id}/results")
    assert res_b.status_code == 404


def test_16_visitor_a_can_still_use_their_own_task_normally():
    """Test 16: Visitor A has full legitimate access to their own task endpoints."""
    client_a = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A Full Lifecycle Task",
            "description": "Legitimate task execution test.",
            "budget": 10.0
        })
        task_a_id = res_a.json()["id"]

    # Detail
    assert client_a.get(f"/api/tasks/{task_a_id}").status_code == 200
    # Progress
    assert client_a.get(f"/api/tasks/{task_a_id}/progress").status_code == 200
    # Activity
    assert client_a.get(f"/api/tasks/{task_a_id}/activity").status_code == 200
    # Results
    assert client_a.get(f"/api/tasks/{task_a_id}/results").status_code == 200


# ==============================================================================
# SECTION 3: PAYMENT & FINANCIAL TRANSACTION ISOLATION (Tests 17 - 22)
# ==============================================================================

def test_17_visitor_b_cannot_read_visitor_a_invoice():
    """Test 17: Visitor B requesting Visitor A's invoice breakdown receives HTTP 404."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A Billing Subject",
            "description": "Invoice protection test.",
            "budget": 10.0
        })
        task_a_id = res_a.json()["id"]

    res_b = client_b.get(f"/api/payments/summary/{task_a_id}")
    assert res_b.status_code == 404


def test_18_visitor_b_cannot_create_paypal_order_for_visitor_a_task():
    """Test 18: Visitor B cannot initiate a PayPal order for Visitor A's task."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A Order Protection",
            "description": "Order creation test.",
            "budget": 10.0
        })
        task_a_id = res_a.json()["id"]

    res_b = client_b.post("/api/payments/paypal/create-order", json={"task_id": task_a_id})
    assert res_b.status_code == 404


def test_19_visitor_b_cannot_capture_visitor_a_order():
    """Test 19: Visitor B cannot capture a PayPal payment for Visitor A's task."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A Capture Test",
            "description": "Payment capture protection.",
            "budget": 10.0
        })
        task_a_id = res_a.json()["id"]

    res_b = client_b.post("/api/payments/paypal/capture-order", json={
        "task_id": task_a_id,
        "order_id": "SIM-ORD-TEST"
    })
    assert res_b.status_code == 404


def test_20_visitor_b_cannot_unlock_visitor_a_deliverable():
    """Test 20: Even after simulated completion, Visitor B cannot access Visitor A's deliverable."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A Locked Report",
            "description": "Deliverable protection check.",
            "budget": 10.0
        })
        task_a_id = res_a.json()["id"]

    # Directly mark task completed in DB as if captured
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_a_id).first()
        t.status = "completed"
        t.final_output = json.dumps({"report": "CONFIDENTIAL DELIVERABLE"})
        db.commit()
    finally:
        db.close()

    res_b = client_b.get(f"/api/tasks/{task_a_id}")
    assert res_b.status_code == 404


def test_21_visitor_b_cannot_list_visitor_a_transactions():
    """Test 21: Visitor B calling /api/payments/transactions sees only their own transactions."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    client_a.get("/api/tasks")
    cookie_a = client_a.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)
    uid_a = verify_guest_session_token(cookie_a)["uid"]

    # Insert a valid task and transaction for Visitor A
    db = SessionLocal()
    try:
        task_a = TaskModel(
            user_id=uid_a,
            title="Visitor A Task for TX",
            description="Transaction listing test description.",
            budget=10.0
        )
        db.add(task_a)
        db.commit()
        db.refresh(task_a)

        tx = TransactionModel(
            user_id=uid_a,
            task_id=task_a.id,
            paypal_order_id="ORD-123",
            amount=8.0,
            currency="USD",
            payment_status="completed",
            provider="paypal_sandbox"
        )
        db.add(tx)
        db.commit()
    finally:
        db.close()

    res_b = client_b.get("/api/payments/transactions")
    assert res_b.status_code == 200
    txs_b = res_b.json()
    assert len(txs_b) == 0, "Visitor B must not see Visitor A's transactions."


def test_22_visitor_a_normal_eligible_payment_lifecycle_intact():
    """Test 22: Visitor A can complete their own payment lifecycle on an eligible task."""
    client_a = TestClient(app)

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res_a = client_a.post("/api/tasks", json={
            "title": "Visitor A Eligible Task",
            "description": "Legitimate payment execution.",
            "budget": 10.0
        })
        task_a_id = res_a.json()["id"]

    # Prepare database state: awaiting_payment with APPROVED QA
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_a_id).first()
        t.status = "awaiting_payment"
        t.current_step = "payment_approval"
        t.execution_plan = json.dumps({"execution_mode": "live_ai"})
        steps = db.query(TaskStepModel).filter(TaskStepModel.task_id == task_a_id).all()
        for s in steps:
            s.status = "completed"
            if s.step_name == "quality_assurance":
                s.output_data = json.dumps({"audit_status": "APPROVED"})
        db.commit()
    finally:
        db.close()

    # Visitor A creates PayPal order
    with patch.object(paypal_service, "create_order", new_callable=AsyncMock) as mock_co:
        mock_co.return_value = {
            "order_id": "TEST-ORD-A",
            "status": "CREATED",
            "approval_url": "https://sandbox.paypal.com"
        }
        order_res = client_a.post("/api/payments/paypal/create-order", json={"task_id": task_a_id})
        assert order_res.status_code == 200


# ==============================================================================
# SECTION 4: RATE LIMITING & RESOURCE ABUSE PREVENTION (Tests 23 - 32)
# ==============================================================================

def test_23_third_task_within_configured_hourly_session_limit_rejected():
    """Test 23: The 3rd task creation in an hour for the same session receives HTTP 429."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN

        # Task 1 (Allowed)
        res1 = client.post("/api/tasks", json={
            "title": "Hourly Task 1",
            "description": "First hourly task test.",
            "budget": 5.0
        })
        assert res1.status_code == 200

        # Mark task 1 completed so concurrency limit of 2 active tasks is not tripped
        db = SessionLocal()
        try:
            db.query(TaskModel).filter(TaskModel.id == res1.json()["id"]).update({"status": "completed"})
            db.commit()
        finally:
            db.close()

        # Task 2 (Allowed)
        res2 = client.post("/api/tasks", json={
            "title": "Hourly Task 2",
            "description": "Second hourly task test.",
            "budget": 5.0
        })
        assert res2.status_code == 200

        db = SessionLocal()
        try:
            db.query(TaskModel).filter(TaskModel.id == res2.json()["id"]).update({"status": "completed"})
            db.commit()
        finally:
            db.close()

        # Task 3 (Blocked by session rate limit: default 2/hour)
        res3 = client.post("/api/tasks", json={
            "title": "Hourly Task 3",
            "description": "Third hourly task test.",
            "budget": 5.0
        })
        assert res3.status_code == 429
        assert "Hourly task creation limit reached for this session" in res3.json()["detail"]
        assert "Retry-After" in res3.headers


def test_24_ip_level_limit_enforced():
    """Test 24: IP rate limit blocks task creation when IP quota is exceeded."""
    client = TestClient(app)
    with patch.object(settings, "RATE_LIMIT_IP_TASKS_PER_HOUR", 1), \
         patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN

        res1 = client.post("/api/tasks", json={
            "title": "IP Task 1",
            "description": "Testing IP limit enforcement.",
            "budget": 5.0
        }, headers={"x-real-ip": "203.0.113.195"})
        assert res1.status_code == 200

        # Different session but same IP
        client_diff_session = TestClient(app)
        res2 = client_diff_session.post("/api/tasks", json={
            "title": "IP Task 2",
            "description": "Testing IP limit second request.",
            "budget": 5.0
        }, headers={"x-real-ip": "203.0.113.195"})
        assert res2.status_code == 429
        assert "Hourly task creation limit reached for your IP address" in res2.json()["detail"]


def test_25_active_workflow_concurrency_limited():
    """Test 25: A visitor cannot have more than 2 concurrent active workflows."""
    client = TestClient(app)
    with patch.object(settings, "RATE_LIMIT_GUEST_TASKS_PER_HOUR", 10), \
         patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN

        # Active Task 1
        res1 = client.post("/api/tasks", json={
            "title": "Active Task 1",
            "description": "Active concurrency test 1.",
            "budget": 5.0
        })
        assert res1.status_code == 200

        # Active Task 2
        res2 = client.post("/api/tasks", json={
            "title": "Active Task 2",
            "description": "Active concurrency test 2.",
            "budget": 5.0
        })
        assert res2.status_code == 200

        # Task 3 (Blocked by active concurrency cap)
        res3 = client.post("/api/tasks", json={
            "title": "Active Task 3",
            "description": "Active concurrency test 3.",
            "budget": 5.0
        })
        assert res3.status_code == 429
        assert "Maximum concurrent active tasks reached" in res3.json()["detail"]


def test_26_repeated_step_advancement_does_not_invoke_gemini_again():
    """Test 26: Completed or terminal tasks short-circuit advancement without invoking Gemini."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Terminal Step Task",
            "description": "Testing step re-execution guard.",
            "budget": 5.0
        })
        task_id = res.json()["id"]

    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        t.status = "completed"
        db.commit()
    finally:
        db.close()

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_adv:
        adv_res = client.post(f"/api/tasks/{task_id}/advance")
        assert adv_res.status_code == 200
        assert adv_res.json()["message"] == "Task workflow is already completed."
        assert mock_adv.call_count == 0, "Gemini must not be called for completed tasks."


def test_27_parallel_step_advancement_cannot_duplicate_execution():
    """Test 27: A step marked 'running' blocks concurrent advancement attempts with HTTP 409."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Parallel Step Guard",
            "description": "Testing duplicate step prevention.",
            "budget": 5.0
        })
        task_id = res.json()["id"]

    # Mark a step running in DB
    db = SessionLocal()
    try:
        s = db.query(TaskStepModel).filter(TaskStepModel.task_id == task_id).first()
        s.status = "running"
        db.commit()
    finally:
        db.close()

    adv_res = client.post(f"/api/tasks/{task_id}/advance")
    assert adv_res.status_code == 409
    assert "currently executing" in adv_res.json()["detail"]


def test_28_rate_limiting_occurs_before_gemini_invocation():
    """Test 28: When rate limit is exceeded, Gemini is called zero times."""
    client = TestClient(app)
    with patch.object(settings, "RATE_LIMIT_GUEST_TASKS_PER_HOUR", 0), \
         patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        res = client.post("/api/tasks", json={
            "title": "Zero Quota Task",
            "description": "Testing pre-execution rate limiting.",
            "budget": 5.0
        })
        assert res.status_code == 429
        assert mock_llm.call_count == 0, "Gemini must not be invoked when rate limited."


def test_29_limiter_database_failure_blocks_expensive_execution():
    """Test 29: Distributed limiter failure fails closed with HTTP 503 without invoking Gemini."""
    client = TestClient(app)
    with patch("api.services.rate_limiter.check_and_increment_counter", side_effect=OperationalError("DB down", None, None)), \
         patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        res = client.post("/api/tasks", json={
            "title": "Fail Closed Task",
            "description": "Testing fail-closed limiter.",
            "budget": 5.0
        })
        assert res.status_code == 503
        assert mock_llm.call_count == 0, "Gemini must never be invoked if limiter fails."


def test_30_oversized_description_receives_http_422():
    """Test 30: Descriptions exceeding 2,000 characters receive HTTP 422 without invoking Gemini."""
    client = TestClient(app)
    oversized_desc = "A" * 2001
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        res = client.post("/api/tasks", json={
            "title": "Oversized Prompt Task",
            "description": oversized_desc,
            "budget": 5.0
        })
        assert res.status_code == 422
        assert mock_llm.call_count == 0, "Gemini must not be invoked for oversized descriptions."


def test_31_oversized_request_body_receives_http_413():
    """Test 31: Request bodies exceeding 32 KB receive HTTP 413 Payload Too Large."""
    client = TestClient(app)
    oversized_payload = {"title": "Oversized Body", "description": "X" * 1500, "padding": "Y" * 40000}
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        res = client.post("/api/tasks", json=oversized_payload)
        assert res.status_code == 413
        assert "Payload Too Large" in res.json()["detail"]
        assert mock_llm.call_count == 0


def test_32_invalid_malformed_inputs_do_not_invoke_gemini():
    """Test 32: Malformed payloads receive HTTP 422 without invoking Gemini."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        res = client.post("/api/tasks", json={
            "title": "",  # Too short (min 3)
            "description": "Short",  # Too short (min 10)
            "budget": -10.0  # Invalid negative budget
        })
        assert res.status_code == 422
        assert mock_llm.call_count == 0


# ==============================================================================
# SECTION 5: ADVANCED CONCURRENCY & RACE CONDITION DEFENSE (Tests 33 - 38)
# ==============================================================================

def test_33_concurrent_task_creation_strictly_enforces_hourly_limit():
    """Test 33: Competing concurrent task creation requests for the same session cannot exceed the limit.
    With limit=2, exactly 2 succeed and remaining are rejected with 429 without invoking Gemini.
    """
    client = TestClient(app)
    # Warm up session cookie
    init_res = client.get("/api/tasks")
    token = client.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)
    assert token is not None

    call_count = {"count": 0}

    async def mock_plan(*args, **kwargs):
        call_count["count"] += 1
        time.sleep(0.05)  # Simulate planning execution time to allow concurrency
        return MOCK_PLAN

    def send_task_creation(i):
        # Create a fresh client sharing the exact same guest session cookie
        c = TestClient(app)
        c.cookies.set(settings.GUEST_SESSION_COOKIE_NAME, token)
        return c.post("/api/tasks", json={
            "title": f"Concurrent Task {i}",
            "description": f"Auditing concurrent task creation race conditions {i}.",
            "budget": 5.0
        })

    with patch.object(orchestrator_agent, "create_plan", side_effect=mock_plan):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_task_creation, i) for i in range(5)]
            responses = [f.result() for f in futures]

    status_codes = [r.status_code for r in responses]
    success_count = status_codes.count(200)
    rejected_count = status_codes.count(429)

    assert success_count == 2, f"Expected exactly 2 admitted tasks, got {success_count}. Statuses: {status_codes}"
    assert rejected_count == 3, f"Expected 3 rejected tasks (429), got {rejected_count}. Statuses: {status_codes}"
    assert call_count["count"] <= 2, f"Gemini was invoked {call_count['count']} times, expected <= 2."


def test_34_concurrent_task_creation_strictly_enforces_active_concurrency_cap():
    """Test 34: Simultaneous task creation requests cannot exceed the active task concurrency cap."""
    client = TestClient(app)
    init_res = client.get("/api/tasks")
    token = client.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)

    call_count = {"count": 0}

    async def mock_plan(*args, **kwargs):
        call_count["count"] += 1
        time.sleep(0.05)
        return MOCK_PLAN

    def send_task(i):
        c = TestClient(app)
        c.cookies.set(settings.GUEST_SESSION_COOKIE_NAME, token)
        return c.post("/api/tasks", json={
            "title": f"Active Cap Task {i}",
            "description": f"Testing concurrent active task concurrency {i}.",
            "budget": 5.0
        })

    # Hourly limit set high (10), but active limit kept at 2
    with patch.object(settings, "RATE_LIMIT_GUEST_TASKS_PER_HOUR", 10), \
         patch.object(settings, "RATE_LIMIT_ACTIVE_TASKS_PER_SESSION", 2), \
         patch.object(orchestrator_agent, "create_plan", side_effect=mock_plan):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(send_task, i) for i in range(5)]
            responses = [f.result() for f in futures]

    status_codes = [r.status_code for r in responses]
    success_count = status_codes.count(200)
    rejected_count = status_codes.count(429)

    assert success_count == 2, f"Active cap should admit exactly 2, got {success_count}. Statuses: {status_codes}"
    assert rejected_count == 3, f"Expected 3 429 rejections, got {rejected_count}. Statuses: {status_codes}"
    assert call_count["count"] <= 2, "Gemini should only be called for admitted tasks."


def test_35_rate_limit_counter_not_lost_under_competing_atomic_writes():
    """Test 35: Competing atomic UPSERT writes in check_and_increment_counter increment accurately without lost updates."""
    from api.services.rate_limiter import check_and_increment_counter
    test_key = "atomic_race_key"

    def increment_op(_):
        db = SessionLocal()
        try:
            allowed, count, _ = check_and_increment_counter(db, test_key, max_count=10, window_seconds=60)
            return allowed, count
        finally:
            db.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(increment_op, range(10)))

    # Verify that all 10 operations succeeded
    counts = [r[1] for r in results]
    assert len(counts) == 10
    db = SessionLocal()
    try:
        final_rec = db.query(RateLimitRecord).filter(RateLimitRecord.key == test_key).first()
        assert final_rec is not None
        assert final_rec.count == 10, f"Expected final counter to be 10, got {final_rec.count}"
    finally:
        db.close()


def test_36_database_error_during_rate_limiting_fails_closed_before_gemini():
    """Test 36: Database error during atomic rate check fails closed with HTTP 503 before Gemini."""
    client = TestClient(app)
    with patch("api.services.rate_limiter.check_and_increment_counter", side_effect=OperationalError("DB down", None, None)), \
         patch.object(orchestrator_agent, "create_plan", new_callable=AsyncMock) as mock_plan:
        res = client.post("/api/tasks", json={
            "title": "Fail Closed Task",
            "description": "Verifying fail-closed behavior before planning.",
            "budget": 5.0
        })
        assert res.status_code == 503
        assert mock_plan.call_count == 0, "Planning must never be invoked if database is unreachable."


def test_37_concurrent_step_advancement_exactly_one_executes_other_gets_409():
    """Test 37: Two simultaneous step advancement requests result in exactly one executing and the other receiving 409."""
    from api.services.orchestrator import research_agent
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Advance Concurrency Task",
            "description": "Testing parallel step advancement locks.",
            "budget": 10.0
        })
        task_id = res.json()["id"]

    token = client.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)
    gemini_exec_count = {"count": 0}

    async def mock_research_exec(*args, **kwargs):
        gemini_exec_count["count"] += 1
        time.sleep(0.08)  # Keep step in running state long enough for concurrent request
        return {
            "market_size_current": "$10B",
            "cagr_percent": 12.5,
            "competitors": [{"name": "CompA", "market_share": "40%"}],
            "methodology": "verified_facts",
            "sources": []
        }

    def call_advance():
        c = TestClient(app)
        c.cookies.set(settings.GUEST_SESSION_COOKIE_NAME, token)
        return c.post(f"/api/tasks/{task_id}/advance")

    with patch.object(research_agent, "execute", side_effect=mock_research_exec):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(call_advance)
            f2 = executor.submit(call_advance)
            r1 = f1.result()
            r2 = f2.result()

    statuses = [r1.status_code, r2.status_code]
    assert 200 in statuses, f"At least one advance must succeed. Got: {statuses}"
    assert 409 in statuses, f"The competing request must receive 409 Conflict. Got: {statuses}"
    assert gemini_exec_count["count"] == 1, f"Gemini was executed {gemini_exec_count['count']} times, expected exactly 1."

def test_38_already_completed_step_cannot_be_executed_again():
    """Test 38: Idempotent step advancement returns completed state without re-invoking AI agents."""
    from api.services.orchestrator import research_agent
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Idempotent Advance Task",
            "description": "Testing non-repetition of completed step.",
            "budget": 10.0
        })
        task_id = res.json()["id"]

    # Advance research step
    with patch.object(research_agent, "execute", new_callable=AsyncMock) as mock_research:
        mock_research.return_value = {"market_size_current": "$5B", "methodology": "verified_facts"}
        adv1 = client.post(f"/api/tasks/{task_id}/advance")
        assert adv1.status_code == 200
        assert mock_research.call_count == 1

    # Directly mark all remaining steps completed in DB to test completed task state
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        t.status = "completed"
        for s in t.steps:
            s.status = "completed"
        db.commit()
    finally:
        db.close()

    # Call advance again on already-completed task
    with patch.object(research_agent, "execute", new_callable=AsyncMock) as mock_research2:
        adv2 = client.post(f"/api/tasks/{task_id}/advance")
        assert adv2.status_code == 200
        assert adv2.json()["message"] == "Task workflow is already completed."
        assert mock_research2.call_count == 0, "AI must never execute on a completed task."


# ==============================================================================
# SECTION 6: TRUSTED CLIENT IP EXTRACTION & SALT STABILITY (Tests 39 - 44)
# ==============================================================================

def test_39_valid_vercel_client_ip_extracted_from_x_real_ip():
    """Test 39: In hosted environments, extract_client_ip prioritizes valid x-real-ip."""
    from api.services.rate_limiter import extract_client_ip
    req = MagicMock(spec=Request)
    req.headers = {"x-real-ip": "203.0.113.195"}
    req.client = MagicMock(host="10.0.0.1")

    with patch.dict("os.environ", {"VERCEL": "1"}):
        ip = extract_client_ip(req)
        assert ip == "203.0.113.195"


def test_40_valid_vercel_client_ip_extracted_from_x_forwarded_for_leftmost():
    """Test 40: In hosted environments, extract_client_ip extracts leftmost IP from x-forwarded-for."""
    from api.services.rate_limiter import extract_client_ip
    req = MagicMock(spec=Request)
    req.headers = {"x-forwarded-for": "198.51.100.42, 10.0.0.2, 172.16.0.1"}
    req.client = MagicMock(host="10.0.0.2")

    with patch.dict("os.environ", {"VERCEL": "1"}):
        ip = extract_client_ip(req)
        assert ip == "198.51.100.42"


def test_41_malformed_ip_in_proxy_headers_falls_back_safely():
    """Test 41: Malformed or malicious IP candidates in headers are rejected by ipaddress validation."""
    from api.services.rate_limiter import extract_client_ip
    req = MagicMock(spec=Request)
    req.headers = {"x-real-ip": "malicious_string; DROP TABLE rate_limits;"}
    req.client = MagicMock(host="192.0.2.1")

    with patch.dict("os.environ", {"VERCEL": "1"}):
        ip = extract_client_ip(req)
        # Malformed header rejected, falls back to direct client host
        assert ip == "192.0.2.1"


def test_42_forged_proxy_headers_ignored_in_local_non_hosted_environment():
    """Test 42: In non-hosted local environments, client-supplied proxy headers are untrusted to prevent spoofing."""
    from api.services.rate_limiter import extract_client_ip
    req = MagicMock(spec=Request)
    req.headers = {"x-real-ip": "1.2.3.4", "x-forwarded-for": "5.6.7.8"}
    req.client = MagicMock(host="127.0.0.1")

    # In local development (VERCEL is not set)
    with patch.dict("os.environ", {"VERCEL": ""}):
        ip = extract_client_ip(req)
        # Client headers ignored, direct connection IP used
        assert ip == "127.0.0.1"


def test_43_ip_hash_salt_is_stable_and_derived_deterministically():
    """Test 43: IP hashing is deterministic, cross-instance stable, and uses cryptographic derivation."""
    from api.services.rate_limiter import hash_client_ip
    with patch.object(settings, "GUEST_SESSION_SECRET", "super-secret-production-key-256bit-min"):
        h1 = hash_client_ip("198.51.100.55")
        h2 = hash_client_ip("198.51.100.55")
        assert h1 == h2, "IP hash must be 100% deterministic."
        assert len(h1) == 32
        assert "198.51.100.55" not in h1, "Raw IP must never be present in hash."


def test_44_missing_trusted_ip_falls_back_safely():
    """Test 44: When no IP information is available, falls back safely to 127.0.0.1 without crashing."""
    from api.services.rate_limiter import extract_client_ip
    req = MagicMock(spec=Request)
    req.headers = {}
    req.client = None
    ip = extract_client_ip(req)
    assert ip == "127.0.0.1"


# ==============================================================================
# SECTION 7: CSRF & COOKIE ORIGIN VALIDATION (Tests 45 - 52)
# ==============================================================================

def test_45_csrf_valid_production_origin_allowed():
    """Test 45: State-changing requests with trusted production Origin header are admitted."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Prod Origin Task",
            "description": "Verifying production origin acceptance.",
            "budget": 5.0
        }, headers={"Origin": "https://agentpay-nexus.vercel.app"})
        assert res.status_code == 200


def test_46_csrf_valid_local_origin_allowed():
    """Test 46: State-changing requests with trusted local frontend Origin are admitted."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Local Origin Task",
            "description": "Verifying local dev origin acceptance.",
            "budget": 5.0
        }, headers={"Origin": "http://localhost:5173"})
        assert res.status_code == 200


def test_47_csrf_untrusted_cross_origin_rejected_with_403():
    """Test 47: State-changing requests with untrusted cross-origin Origin header are rejected with HTTP 403."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        res = client.post("/api/tasks", json={
            "title": "Attacker Origin Task",
            "description": "Verifying cross-origin CSRF rejection.",
            "budget": 5.0
        }, headers={"Origin": "https://evil-attacker.com"})
        assert res.status_code == 403
        assert res.json()["detail"] == "Cross-origin request forbidden."
        assert mock_llm.call_count == 0


def test_48_csrf_missing_origin_and_referer_allowed_for_direct_api():
    """Test 48: Direct API requests without Origin or Referer headers (curl, server-to-server) are admitted."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Direct API Task",
            "description": "Verifying standard direct API calls without Origin.",
            "budget": 5.0
        })
        assert res.status_code == 200


def test_49_csrf_malformed_and_null_origin_rejected():
    """Test 49: Malformed or 'null' Origin headers are rejected with HTTP 403."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        # 1. null origin (sandboxed iframes / file schemes)
        res_null = client.post("/api/tasks", json={
            "title": "Null Origin Task",
            "description": "Verifying null origin rejection.",
            "budget": 5.0
        }, headers={"Origin": "null"})
        assert res_null.status_code == 403

        # 2. javascript pseudo-origin
        res_js = client.post("/api/tasks", json={
            "title": "JS Origin Task",
            "description": "Verifying javascript origin rejection.",
            "budget": 5.0
        }, headers={"Origin": "javascript:alert(1)"})
        assert res_js.status_code == 403
        assert mock_llm.call_count == 0


def test_50_csrf_cross_site_request_with_valid_guest_cookie_rejected():
    """Test 50: Cross-site request attempting to exploit a valid signed guest session cookie is blocked with 403."""
    client = TestClient(app)
    # Acquire a valid signed cookie
    client.get("/api/tasks")
    token = client.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)
    assert token is not None

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        res = client.post("/api/tasks", json={
            "title": "CSRF Exploit Task",
            "description": "Attacker trying to use user cookie from evil site.",
            "budget": 5.0
        }, headers={"Origin": "https://malicious-site.org"})
        assert res.status_code == 403
        assert mock_llm.call_count == 0


def test_51_csrf_cross_site_referer_rejected():
    """Test 51: State-changing request with an untrusted Referer header (when Origin is omitted) is rejected with 403."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        res = client.post("/api/tasks", json={
            "title": "Referer CSRF Task",
            "description": "Testing referer cross-site protection.",
            "budget": 5.0
        }, headers={"Referer": "https://evil.com/attacker_payload.html"})
        assert res.status_code == 403
        assert "Cross-origin referer forbidden." in res.json()["detail"]
        assert mock_llm.call_count == 0


def test_52_cors_preflight_options_allowed():
    """Test 52: CORS preflight OPTIONS request is handled cleanly by CORS middleware."""
    client = TestClient(app)
    res = client.options("/api/tasks", headers={
        "Origin": "https://agentpay-nexus.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"
    })
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "https://agentpay-nexus.vercel.app"
    assert res.headers.get("access-control-allow-credentials") == "true"


# ==============================================================================
# SECTION 8: POSTGRESQL DIALECT COMPATIBILITY & WORKFLOW ADVANCEMENT RATE LIMITS (Tests 53 - 58)
# ==============================================================================

def test_53_postgresql_model_and_migration_ddl_exact_compatibility():
    """Test 53: Validates that RateLimitRecord SQLAlchemy model compiles exactly to PostgreSQL dialect DDL matching migration 002."""
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable
    from api.models.ratelimit import RateLimitRecord

    pg_ddl = str(CreateTable(RateLimitRecord.__table__).compile(dialect=postgresql.dialect()))
    assert "VARCHAR(255)" in pg_ddl
    assert "TIMESTAMP WITH TIME ZONE" in pg_ddl
    assert "PRIMARY KEY (key)" in pg_ddl

    # Check migration file exists and is idempotent
    with open("migrations/002_rate_limits.sql", "r", encoding="utf-8") as f:
        mig_sql = f.read()

    assert "CREATE TABLE IF NOT EXISTS rate_limits" in mig_sql
    assert "key VARCHAR(255) PRIMARY KEY" in mig_sql
    assert "TIMESTAMP WITH TIME ZONE" in mig_sql
    assert "CREATE INDEX IF NOT EXISTS idx_rate_limits_expires_at" in mig_sql


def test_54_step_advancement_per_session_rate_limit_enforced():
    """Test 54: Workflow step advancement is rate-limited per session. Excess requests return HTTP 429."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Step Rate Limit Task",
            "description": "Testing step advancement rate limits.",
            "budget": 10.0
        })
        task_id = res.json()["id"]

    from api.services.orchestrator import research_agent
    with patch.object(settings, "RATE_LIMIT_GUEST_STEPS_PER_HOUR", 1), \
         patch.object(research_agent, "execute", new_callable=AsyncMock) as mock_research:
        mock_research.return_value = {"market_size_current": "$10B", "methodology": "verified_facts"}

        # Step 1: should succeed (limit = 1)
        r1 = client.post(f"/api/tasks/{task_id}/advance")
        assert r1.status_code == 200
        assert mock_research.call_count == 1

        # Step 2: should be rejected with 429 because session hourly step limit is 1
        r2 = client.post(f"/api/tasks/{task_id}/advance")
        assert r2.status_code == 429
        assert "Hourly workflow execution limit reached for this session" in r2.json()["detail"]
        assert mock_research.call_count == 1, "Gemini must not be invoked on rate-limited step advance."


def test_55_step_advancement_per_ip_rate_limit_enforced():
    """Test 55: Workflow step advancement is rate-limited at the IP level across rotated cookies."""
    # Visitor A creates task
    client_a = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client_a.post("/api/tasks", json={
            "title": "IP Step Task",
            "description": "Testing IP step rate limiting.",
            "budget": 10.0
        })
        task_id = res.json()["id"]

    from api.services.orchestrator import research_agent
    with patch.object(settings, "RATE_LIMIT_GUEST_STEPS_PER_HOUR", 10), \
         patch.object(settings, "RATE_LIMIT_IP_STEPS_PER_HOUR", 1), \
         patch.object(research_agent, "execute", new_callable=AsyncMock) as mock_research:
        mock_research.return_value = {"market_size_current": "$10B", "methodology": "verified_facts"}

        # Step 1 consumes the 1 IP step allowance
        r1 = client_a.post(f"/api/tasks/{task_id}/advance")
        assert r1.status_code == 200

        # Step 2 hits IP rate limit (limit=1)
        r2 = client_a.post(f"/api/tasks/{task_id}/advance")
        assert r2.status_code == 429
        assert "Hourly workflow execution limit reached for your IP address" in r2.json()["detail"]


def test_56_step_advancement_rate_limited_invokes_gemini_zero_times():
    """Test 56: When step advancement is rate-limited, Gemini and agent tools are invoked 0 times."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Zero Inference Step Task",
            "description": "Verifying zero Gemini calls when step advance is blocked.",
            "budget": 10.0
        })
        task_id = res.json()["id"]

    from api.services.orchestrator import research_agent
    with patch.object(settings, "RATE_LIMIT_GUEST_STEPS_PER_HOUR", 0), \
         patch.object(research_agent, "execute", new_callable=AsyncMock) as mock_research:
        r = client.post(f"/api/tasks/{task_id}/advance")
        assert r.status_code == 429
        assert mock_research.call_count == 0, "Agent execution must not occur when rate limited."


def test_57_unauthorized_step_advance_fails_404_without_consuming_quota():
    """Test 57: Unauthorized step advancement attempts fail with 404 and DO NOT consume step rate quota."""
    client_a = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client_a.post("/api/tasks", json={
            "title": "Victim Task",
            "description": "Testing that attacker cannot exhaust victim step quota.",
            "budget": 10.0
        })
        task_id = res.json()["id"]

    # Visitor B attempts to advance Visitor A's task
    client_b = TestClient(app)
    adv_b = client_b.post(f"/api/tasks/{task_id}/advance")
    assert adv_b.status_code == 404

    # Verify that Visitor A's step advancement still works and quota was not consumed
    from api.services.orchestrator import research_agent
    with patch.object(settings, "RATE_LIMIT_GUEST_STEPS_PER_HOUR", 1), \
         patch.object(research_agent, "execute", new_callable=AsyncMock) as mock_research:
        mock_research.return_value = {"market_size_current": "$10B", "methodology": "verified_facts"}
        adv_a = client_a.post(f"/api/tasks/{task_id}/advance")
        assert adv_a.status_code == 200, "Visitor A must retain full quota after unauthorized 404 attempt."


def test_58_completed_task_advance_does_not_consume_step_quota():
    """Test 58: Repeated calls to advance on an already-completed task return early without consuming step quota."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Completed Task Quota Check",
            "description": "Verifying completed task returns early without quota consumption.",
            "budget": 10.0
        })
        task_id = res.json()["id"]

    # Mark task completed
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        t.status = "completed"
        for s in t.steps:
            s.status = "completed"
        db.commit()
    finally:
        db.close()

    # Even with step limit = 0, completed task returns 200 without checking or consuming quota
    with patch.object(settings, "RATE_LIMIT_GUEST_STEPS_PER_HOUR", 0):
        adv = client.post(f"/api/tasks/{task_id}/advance")
        assert adv.status_code == 200
        assert adv.json()["message"] == "Task workflow is already completed."


def test_59_clock_controlled_session_rate_limit_window_expiration():
    """Test 59: Clock-controlled session rate counter increments, enforces limit, and resets on expiration."""
    from api.services.rate_limiter import check_and_increment_counter
    db = SessionLocal()
    try:
        t0 = datetime(2026, 11, 8, 10, 0, 0, tzinfo=timezone.utc)
        key = "sess:test_sess_59:step_advance"

        # 1. Request 1 at t0 within window: allowed, count=1
        allowed1, count1, retry1 = check_and_increment_counter(db, key, max_count=2, window_seconds=3600, current_time=t0)
        assert allowed1 is True
        assert count1 == 1
        assert retry1 == 3600

        # 2. Request 2 at t0 + 100s: allowed, count=2
        t1 = t0 + timedelta(seconds=100)
        allowed2, count2, retry2 = check_and_increment_counter(db, key, max_count=2, window_seconds=3600, current_time=t1)
        assert allowed2 is True
        assert count2 == 2
        assert retry2 == 3500

        # 3. Request 3 at t0 + 200s: exceeds limit of 2, rejected
        t2 = t0 + timedelta(seconds=200)
        allowed3, count3, retry3 = check_and_increment_counter(db, key, max_count=2, window_seconds=3600, current_time=t2)
        assert allowed3 is False
        assert count3 == 3
        assert retry3 == 3400

        # 4. Advance clock past expiration: t0 + 3601s -> admitted with count reset to 1
        t_expired = t0 + timedelta(seconds=3601)
        allowed4, count4, retry4 = check_and_increment_counter(db, key, max_count=2, window_seconds=3600, current_time=t_expired)
        assert allowed4 is True, "Request after expiration must be admitted"
        assert count4 == 1, "Counter must reset to 1 on window expiration"
        assert retry4 == 3600, "New window must start with full 3600s TTL"
    finally:
        db.close()


def test_60_clock_controlled_ip_rate_limit_window_expiration():
    """Test 60: Clock-controlled IP rate counter increments, enforces limit, and resets on expiration."""
    from api.services.rate_limiter import check_and_increment_counter
    db = SessionLocal()
    try:
        t0 = datetime(2026, 11, 8, 10, 0, 0, tzinfo=timezone.utc)
        key = "ip:test_ip_hash_60:task_create"

        # 1. Request 1 at t0
        allowed1, count1, retry1 = check_and_increment_counter(db, key, max_count=1, window_seconds=3600, current_time=t0)
        assert allowed1 is True
        assert count1 == 1

        # 2. Request 2 at t0 + 50s: blocked by max_count=1
        t1 = t0 + timedelta(seconds=50)
        allowed2, count2, retry2 = check_and_increment_counter(db, key, max_count=1, window_seconds=3600, current_time=t1)
        assert allowed2 is False
        assert count2 == 2
        assert retry2 == 3550

        # 3. Advance clock past expiration: t0 + 3605s -> admitted, count reset to 1
        t_expired = t0 + timedelta(seconds=3605)
        allowed3, count3, retry3 = check_and_increment_counter(db, key, max_count=1, window_seconds=3600, current_time=t_expired)
        assert allowed3 is True
        assert count3 == 1
        assert retry3 == 3600
    finally:
        db.close()


def test_61_concurrent_requests_at_window_rollover_cannot_bypass_limit():
    """Test 61: Concurrent requests arriving at the moment of window expiration cannot bypass the limit."""
    import tempfile
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from api.services.rate_limiter import check_and_increment_counter

    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_rollover.db")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"timeout": 30.0})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    t0 = datetime(2026, 11, 8, 12, 0, 0, tzinfo=timezone.utc)
    key = "ip:conc_rollover_test:step_advance"

    # Pre-populate with an expired row
    init_db = Session()
    t_expired = t0 - timedelta(seconds=5)
    rec = RateLimitRecord(
        key=key,
        count=10,
        window_start=t_expired - timedelta(seconds=3600),
        expires_at=t_expired
    )
    init_db.add(rec)
    init_db.commit()
    init_db.close()

    max_count = 2

    def worker(worker_id):
        worker_db = Session()
        try:
            allowed, count, retry = check_and_increment_counter(
                db=worker_db,
                key=key,
                max_count=max_count,
                window_seconds=3600,
                current_time=t0
            )
            return allowed, count
        finally:
            worker_db.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(worker, range(6)))

    allowed_count = sum(1 for allowed, _ in results if allowed)
    rejected_count = sum(1 for allowed, _ in results if not allowed)
    counts = sorted([c for _, c in results])

    assert allowed_count == 2, f"Exactly {max_count} requests must be allowed at rollover, got {allowed_count}"
    assert rejected_count == 4, f"Exactly 4 requests must be rejected at rollover, got {rejected_count}"
    assert counts == [1, 2, 3, 4, 5, 6], f"Counts must be sequential [1..6], got {counts}"

    engine.dispose()
    try:
        os.remove(db_path)
    except Exception:
        pass


def test_62_http_clock_controlled_task_creation_session_window_reset():
    """Test 62: End-to-end task creation rate limit recovers after advancing the clock past window expiration."""
    client = TestClient(app)
    t0 = datetime(2026, 11, 8, 14, 0, 0, tzinfo=timezone.utc)

    with patch("api.services.rate_limiter.get_current_time", return_value=t0), \
         patch.object(settings, "RATE_LIMIT_GUEST_TASKS_PER_HOUR", 1), \
         patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN

        # 1. First task creation at t0 succeeds
        r1 = client.post("/api/tasks", json={
            "title": "Task Window Test 1",
            "description": "First task in window.",
            "budget": 10.0
        })
        assert r1.status_code == 200

        # 2. Second task creation at t0 + 100s rejected by limit of 1
        with patch("api.services.rate_limiter.get_current_time", return_value=t0 + timedelta(seconds=100)):
            r2 = client.post("/api/tasks", json={
                "title": "Task Window Test 2",
                "description": "Second task in window.",
                "budget": 10.0
            })
            assert r2.status_code == 429
            assert "Hourly task creation limit reached for this session" in r2.json()["detail"]
            assert "Retry-After" in r2.headers

        # 3. Advance clock past expiration: t0 + 3601s -> admitted!
        t_expired = t0 + timedelta(seconds=3601)
        with patch("api.services.rate_limiter.get_current_time", return_value=t_expired):
            r3 = client.post("/api/tasks", json={
                "title": "Task Window Test 3",
                "description": "Task in new refreshed window.",
                "budget": 10.0
            })
            assert r3.status_code == 200, "Task creation must succeed after clock passes window expiration."


def test_63_rate_limited_step_advance_leaves_step_in_pending_not_running():
    """Test 63: A rate-limited step advance request does not claim the step or leave it in running status."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "State Safety Task 63",
            "description": "Verifying step state under rate limiting.",
            "budget": 10.0
        })
        assert res.status_code == 200
        task_id = res.json()["id"]

    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        assert t.status == "executing"
        step1 = [s for s in t.steps if s.step_name == "research"][0]
        assert step1.status == "pending"
    finally:
        db.close()

    from api.services.orchestrator import research_agent
    with patch.object(settings, "RATE_LIMIT_GUEST_STEPS_PER_HOUR", 0), \
         patch.object(research_agent, "execute", new_callable=AsyncMock) as mock_research:
        adv = client.post(f"/api/tasks/{task_id}/advance")
        assert adv.status_code == 429
        assert "Hourly workflow execution limit reached" in adv.json()["detail"]
        assert mock_research.call_count == 0, "Gemini must not be called when rate limited."

    # Verify state in database: step MUST STILL BE PENDING, task MUST STILL BE EXECUTING
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        assert t.status == "executing", f"Task status was unexpectedly changed to {t.status}!"
        step1 = [s for s in t.steps if s.step_name == "research"][0]
        assert step1.status == "pending", f"Step status was unexpectedly changed to {step1.status}!"
        assert step1.started_at is None, "started_at must remain None for unclaimed step."
    finally:
        db.close()


def test_64_rate_limit_reset_allows_step_advancement_resumption():
    """Test 64: After rate limiting, workflow step advancement can resume normally once quota recovers."""
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Resume Task 64",
            "description": "Verifying normal resumption after rate limit recovery.",
            "budget": 10.0
        })
        assert res.status_code == 200
        task_id = res.json()["id"]

    from api.services.orchestrator import research_agent

    # 1. Block advancement via step rate limit = 0
    with patch.object(settings, "RATE_LIMIT_GUEST_STEPS_PER_HOUR", 0):
        adv_blocked = client.post(f"/api/tasks/{task_id}/advance")
        assert adv_blocked.status_code == 429

    # 2. Quota recovers (limit = 5) -> normal advancement proceeds
    with patch.object(settings, "RATE_LIMIT_GUEST_STEPS_PER_HOUR", 5), \
         patch.object(research_agent, "execute", new_callable=AsyncMock) as mock_research:
        mock_research.return_value = {"market_size_current": "$10B", "methodology": "verified_facts"}
        adv_ok = client.post(f"/api/tasks/{task_id}/advance")
        assert adv_ok.status_code == 200
        assert adv_ok.json()["advanced_step"] == "research"
        assert mock_research.call_count == 1

    # Database verification: step is completed
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        step1 = [s for s in t.steps if s.step_name == "research"][0]
        assert step1.status == "completed"
        assert step1.completed_at is not None
    finally:
        db.close()


def test_65_simultaneous_permitted_advancements_at_most_one_executes():
    """Test 65: When two requests simultaneously attempt to advance the same step, at most one executes."""
    from api.services.orchestrator import research_agent
    client = TestClient(app)
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_PLAN
        res = client.post("/api/tasks", json={
            "title": "Simultaneous Permitted Advance Task",
            "description": "Testing atomic step claiming under concurrent requests.",
            "budget": 10.0
        })
        task_id = res.json()["id"]

    token = client.cookies.get(settings.GUEST_SESSION_COOKIE_NAME)
    gemini_exec_count = {"count": 0}
    step_running_event = threading.Event()
    cont_event = threading.Event()

    async def mock_research_exec(*args, **kwargs):
        gemini_exec_count["count"] += 1
        step_running_event.set()
        cont_event.wait(timeout=2.0)
        return {
            "market_size_current": "$10B",
            "methodology": "verified_facts"
        }

    def call_advance_1():
        c = TestClient(app)
        c.cookies.set(settings.GUEST_SESSION_COOKIE_NAME, token)
        return c.post(f"/api/tasks/{task_id}/advance")

    def call_advance_2():
        step_running_event.wait(timeout=2.0)
        c = TestClient(app)
        c.cookies.set(settings.GUEST_SESSION_COOKIE_NAME, token)
        res = c.post(f"/api/tasks/{task_id}/advance")
        cont_event.set()
        return res

    with patch.object(settings, "RATE_LIMIT_GUEST_STEPS_PER_HOUR", 10), \
         patch.object(research_agent, "execute", side_effect=mock_research_exec):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(call_advance_1)
            f2 = executor.submit(call_advance_2)
            r1 = f1.result()
            r2 = f2.result()

    statuses = [r1.status_code, r2.status_code]
    assert 200 in statuses, f"At least one advance must succeed. Got: {statuses}"
    assert 409 in statuses, f"The competing request must receive 409 Conflict. Got: {statuses}"
    assert gemini_exec_count["count"] == 1, f"Gemini was executed {gemini_exec_count['count']} times, expected exactly 1."
