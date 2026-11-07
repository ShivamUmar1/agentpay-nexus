import asyncio
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient
import httpx

from api.main import app
from api.config import settings
from api.services.llm_provider import (
    llm_provider,
    classify_gemini_error,
    parse_retry_delay,
    extract_json,
    extract_topic_title,
    AIError,
    AIErrorKind
)
from api.services.agents.research_agent import ResearchAgent
from api.services.agents.data_analysis_agent import DataAnalysisAgent
from api.services.agents.content_agent import ContentAgent
from api.services.agents.qa_agent import QualityAssuranceAgent
from api.database import get_db, SessionLocal
from api.models.task import TaskModel, TaskStepModel

client = TestClient(app)


# ==============================================================================
# SECTION 8.1 — PROVIDER ERROR CLASSIFICATION TESTS
# ==============================================================================

def test_classify_429_daily_quota_exhaustion():
    body = json.dumps({
        "error": {
            "code": 429,
            "message": "Resource has been exhausted (e.g. check quota). Quota exceeded for quota metric 'Queries' and limit 'Queries per day' of service 'generativelanguage.googleapis.com'.",
            "status": "RESOURCE_EXHAUSTED"
        }
    })
    err = classify_gemini_error(429, body, model="gemini-3-flash-preview")
    assert err.kind == AIErrorKind.QUOTA_EXHAUSTED
    assert err.status_code == 429
    assert "usage limit" in err.user_message or "quota" in err.user_message
    assert err.model == "gemini-3-flash-preview"


def test_classify_429_rpm_retry_after_header():
    body = json.dumps({
        "error": {
            "code": 429,
            "message": "Rate limit exceeded. Too many requests per minute.",
            "status": "RESOURCE_EXHAUSTED"
        }
    })
    headers = {"retry-after": "4"}
    err = classify_gemini_error(429, body, headers=headers, model="gemini-3-flash-preview")
    assert err.kind == AIErrorKind.RATE_LIMIT_TRANSIENT
    assert err.retry_after == 4.0
    assert "rate limit reached" in err.user_message.lower()


def test_classify_429_retry_delay_in_body():
    body = json.dumps({
        "error": {
            "code": 429,
            "message": "Rate limit reached. Please wait before sending more requests per minute.",
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.RetryInfo",
                    "retryDelay": "21s"
                }
            ]
        }
    })
    err = classify_gemini_error(429, body, model="gemini-3-flash-preview")
    assert err.kind == AIErrorKind.RATE_LIMIT_TRANSIENT
    assert err.retry_after == 21.0


def test_classify_503_service_unavailable():
    body = "503 Service Temporarily Unavailable"
    err = classify_gemini_error(503, body, model="gemini-3-flash-preview")
    assert err.kind == AIErrorKind.SERVICE_UNAVAILABLE
    assert err.status_code == 503
    assert "temporarily overloaded" in err.user_message.lower()


def test_classify_401_invalid_key():
    body = json.dumps({
        "error": {
            "code": 401,
            "message": "API key not valid. Please pass a valid API key.",
            "status": "UNAUTHENTICATED"
        }
    })
    err = classify_gemini_error(401, body, model="gemini-3-flash-preview")
    assert err.kind == AIErrorKind.AUTH_ERROR
    assert err.status_code == 401
    assert "authentication failed" in err.user_message.lower()


def test_classify_403_permission_failure():
    body = json.dumps({
        "error": {
            "code": 403,
            "message": "The caller does not have permission to execute the specified operation or billing not enabled.",
            "status": "PERMISSION_DENIED"
        }
    })
    err = classify_gemini_error(403, body, model="gemini-3-flash-preview")
    assert err.kind == AIErrorKind.AUTH_ERROR
    assert err.status_code == 403
    assert "authentication failed" in err.user_message.lower()


def test_classify_404_invalid_model():
    body = json.dumps({
        "error": {
            "code": 404,
            "message": "models/gemini-3.8-flash is not found for API version v1beta",
            "status": "NOT_FOUND"
        }
    })
    err = classify_gemini_error(404, body, model="gemini-3.8-flash")
    assert err.kind == AIErrorKind.MODEL_NOT_FOUND
    assert err.status_code == 404
    assert "gemini-3.8-flash" in err.user_message


def test_extract_json_valid_and_malformed():
    valid = '```json\n{"status": "ok", "count": 42}\n```'
    data = extract_json(valid)
    assert data["status"] == "ok"
    assert data["count"] == 42

    with pytest.raises(ValueError):
        extract_json("Plain text with no JSON braces anywhere.")


@pytest.mark.asyncio
async def test_bounded_no_cascade_on_quota_exhaustion():
    """Verify that on 429 Quota Exhaustion, llm_provider does NOT cascade to fallback models."""
    exhaustion_response = MagicMock(spec=httpx.Response)
    exhaustion_response.status_code = 429
    exhaustion_response.text = json.dumps({
        "error": {
            "code": 429,
            "message": "Quota exceeded for quota metric 'Queries per day'.",
            "status": "RESOURCE_EXHAUSTED"
        }
    })
    exhaustion_response.headers = {}

    call_count = 0

    async def mock_post(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        return exhaustion_response

    with patch.object(settings, "GEMINI_API_KEY", "mock-test-key-12345"):
        with patch("httpx.AsyncClient.post", side_effect=mock_post):
            with pytest.raises(AIError) as exc_info:
                await llm_provider.generate_json("Test prompt", None)

            assert exc_info.value.kind == AIErrorKind.QUOTA_EXHAUSTED
            # Must halt immediately after 1 attempt — no cascading across models with the same project key!
            assert call_count == 1


# ==============================================================================
# SECTION 8.2 — TOPIC RELEVANCE & NO HARDCODED EV LEAK TESTS
# ==============================================================================

def test_offline_scaffold_no_ev_leak_on_unrelated_topics():
    """Verify that offline deterministic scaffolds do NOT leak Indian EV data into unrelated topics."""
    topics = [
        "Analyze the commercial real estate market in New York.",
        "Evaluate cybersecurity startup valuations.",
        "Create a business strategy for a healthcare SaaS company."
    ]

    for topic in topics:
        # Prompt as research
        res = llm_provider._generate_fallback_json(f"Conduct rigorous market research on:\nTitle: {topic}\n", None)
        res_str = json.dumps(res).lower()

        assert "tata motors" not in res_str
        assert "ola electric" not in res_str
        assert "fame-ii" not in res_str
        assert "emps" not in res_str
        assert "battery gigafactory" not in res_str
        assert "3.21 billion" not in res_str
        assert "113.99 billion" not in res_str

        # Prompt as data analysis
        ana = llm_provider._generate_fallback_json(f"Analyze the research data for: {topic}\n", None)
        ana_str = json.dumps(ana).lower()
        assert "tata motors" not in ana_str
        assert "mahindra" not in ana_str
        assert "mg motor" not in ana_str

        # Fallback text
        txt = llm_provider._generate_fallback_text(f"Task Title: {topic}\n", None).lower()
        assert "tata motors" not in txt
        assert "electric vehicle" not in txt


@pytest.mark.asyncio
async def test_live_429_fails_transparently_without_ev_leak():
    """Verify that when 429 occurs on unrelated topics, AIError is raised, NOT fake EV data."""
    exhaustion_response = MagicMock(spec=httpx.Response)
    exhaustion_response.status_code = 429
    exhaustion_response.text = json.dumps({
        "error": {
            "code": 429,
            "message": "Resource has been exhausted (quota exceeded).",
            "status": "RESOURCE_EXHAUSTED"
        }
    })
    exhaustion_response.headers = {}

    unrelated_topic = "Evaluate cybersecurity startup valuations in North America"

    with patch.object(settings, "GEMINI_API_KEY", "mock-key-cyber"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = exhaustion_response
            research_agent = ResearchAgent()
            with pytest.raises(AIError) as exc_info:
                await research_agent.execute(unrelated_topic, "Examine early-stage multiples and SOC-2 moats.")

            assert exc_info.value.kind == AIErrorKind.QUOTA_EXHAUSTED
            assert "usage limit" in exc_info.value.user_message or "quota" in exc_info.value.user_message


# ==============================================================================
# SECTION 8.3 — WORKFLOW INTEGRITY & PAYMENT GATING TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_failed_step_halts_workflow_and_locks_deliverables():
    """Verify that when an agent step encounters AI failure, task fails, deliverable is locked, and no payment is created."""
    exhaustion_response = MagicMock(spec=httpx.Response)
    exhaustion_response.status_code = 429
    exhaustion_response.text = json.dumps({
        "error": {
            "code": 429,
            "message": "Daily quota limit reached.",
            "status": "RESOURCE_EXHAUSTED"
        }
    })
    exhaustion_response.headers = {}

    # Create a task in offline/scaffold mode first so planning succeeds
    with patch.object(settings, "GEMINI_API_KEY", None), patch.object(settings, "OPENAI_API_KEY", None):
        res = client.post("/api/tasks", json={
            "title": "Quantum Computing Market Horizons",
            "description": "Assess superconducting qubit roadmaps.",
            "budget": 10.0,
            "currency": "USD"
        })
        assert res.status_code == 200
        task_id = res.json()["id"]

    # Now simulate live API quota exhaustion on step advance (research step)
    with patch.object(settings, "GEMINI_API_KEY", "mock-active-key"):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = exhaustion_response
            adv_res = client.post(f"/api/tasks/{task_id}/advance")
            assert adv_res.status_code == 429
            detail = adv_res.json()["detail"]
            assert detail["error_kind"] == "QUOTA_EXHAUSTED"

    # Verify task state in database
    task_res = client.get(f"/api/tasks/{task_id}")
    assert task_res.status_code == 200
    task_data = task_res.json()
    assert task_data["status"] == "failed"
    assert task_data["final_output"] is None  # DELIVERABLE MUST REMAIN LOCKED!

    # Verify research step is marked failed
    research_step = [s for s in task_data["steps"] if s["step_name"] == "research"][0]
    assert research_step["status"] == "failed"
    assert research_step["error_message"] is not None
    assert "usage limit" in research_step["error_message"] or "quota" in research_step["error_message"]

    # Verify that trying to create a PayPal order on a failed task is rejected
    pay_res = client.post("/api/payments/paypal/create-order", json={"task_id": task_id})
    assert pay_res.status_code in (400, 422)  # Cannot create payment for failed task!


def test_qa_agent_rejects_empty_or_failed_report():
    """Verify that QA Agent does NOT approve missing or empty deliverables."""
    qa = QualityAssuranceAgent()

    empty_report = {"report_markdown": ""}
    research_data = {"market_size_current": "$5.00B"}
    analysis_data = {"computed_metrics": {"cagr_percent": 20.0}}

    loop = asyncio.new_event_loop()
    try:
        qa_result = loop.run_until_complete(
            qa.execute(
                "Autonomous Fleet Analysis",
                "Study fleet telematics.",
                empty_report,
                research_data,
                analysis_data
            )
        )
    finally:
        loop.close()

    assert qa_result["audit_status"] == "NEEDS_REVISION"
    assert qa_result["constraint_compliance"] is False
    assert qa_result["corrections_required"] is True
    assert qa_result["completeness_score"] < 50


# ==============================================================================
# SECTION 8.4 — SYSTEM STATUS ENDPOINT DIAGNOSTICS TESTS
# ==============================================================================

def test_system_status_responds_instantly_without_external_calls():
    """Verify /api/system/status does NOT make external AI network calls and responds within bounded deadline."""
    with patch.object(llm_provider, "_call_gemini") as mock_gemini:
        t0 = time.time()
        res = client.get("/api/system/status")
        duration_ms = (time.time() - t0) * 1000

        assert res.status_code == 200
        assert duration_ms < 5000  # Well within Vercel's 15s serverless function timeout

        data = res.json()
        assert "service" in data
        assert "database" in data
        assert "ai_orchestration" in data
        assert "payment_gateway" in data

        ai_diag = data["ai_orchestration"]
        assert "provider" in ai_diag
        assert "configured_model" in ai_diag
        assert "status" in ai_diag
        assert "timeout_seconds" in ai_diag

        # CRITICAL: External LLM API must NOT have been called!
        assert mock_gemini.call_count == 0


def test_system_test_ai_endpoint_is_bounded():
    """Verify dedicated /api/system/test-ai handles bounded diagnostics."""
    with patch.object(settings, "GEMINI_API_KEY", None), patch.object(settings, "OPENAI_API_KEY", None):
        res = client.get("/api/system/test-ai")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] in ("not_configured", "demo_fallback", "connected", "error")


# ==============================================================================
# SECTION 8.5 — ZERO FABRICATION & EMPTY CHART DATASET TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_missing_research_data_returns_none_and_empty_charts():
    """Verify that when research data is absent or lacks numbers, data analysis reports metrics as unavailable and charts as []."""
    da = DataAnalysisAgent()
    empty_research = {
        "market_size_current": "Unknown",
        "market_size_projected": "Unavailable",
        "cagr_percent": None,
        "key_competitors": []
    }

    mock_llm_analysis = {
        "computed_metrics": {},
        "market_share_breakdown": [],
        "key_findings": "Numerical baseline metrics unavailable from source research."
    }
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_analysis
        analysis = await da.execute("Cloud Security Solutions", empty_research)

    metrics = analysis.get("computed_metrics", {})
    assert metrics.get("status") == "unavailable"
    assert metrics.get("cagr_percent") is None
    assert analysis.get("chart_revenue_projections") == []
    assert analysis.get("market_share_breakdown") == []
    assert "unavailable" in str(analysis.get("key_findings", "")).lower()

    # Verify content agent does NOT fabricate fake tables or CAGR
    ca = ContentAgent()
    mock_llm_content = {
        "executive_summary": "Executive summary for Cloud Security.",
        "report_markdown": "# Cloud Security Solutions\n\nData Unavailable: Baseline metrics could not be established from research data.",
        "key_takeaways": ["Quantitative metrics could not be verified"],
        "strategic_recommendations": ["Conduct primary research"]
    }
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_content
        content = await ca.execute("Cloud Security Solutions", "Evaluate cloud security.", empty_research, analysis)

    report = content.get("report_markdown", "")
    assert "Data Unavailable" in report or "unavailable" in report.lower()
    assert "$5.0" not in report
    assert "$15.0" not in report


# ==============================================================================
# SECTION 8.6 — OFFLINE SCAFFOLD & SERVER-SIDE PAYMENT RESTRICTIONS
# ==============================================================================

def test_offline_scaffold_creation_and_qa_rejection():
    """Verify tasks created without AI credentials are tagged offline_scaffold and rejected by QA."""
    with patch.object(settings, "GEMINI_API_KEY", None), patch.object(settings, "OPENAI_API_KEY", None):
        res = client.post("/api/tasks", json={
            "title": "Autonomous Supply Chain Analytics",
            "description": "Analyze multi-echelon inventory systems.",
            "budget": 10.0,
            "currency": "USD"
        })
        assert res.status_code == 200
        task_data = res.json()
        assert task_data["execution_mode"] == "offline_scaffold"
        task_id = task_data["id"]

    # Verify QA Agent rejects offline scaffold
    qa = QualityAssuranceAgent()
    loop = asyncio.new_event_loop()
    try:
        qa_out = loop.run_until_complete(
            qa.execute(
                "Autonomous Supply Chain Analytics",
                "Analyze multi-echelon inventory systems.",
                {"report_markdown": "# Scaffold Report", "execution_mode": "offline_scaffold"},
                {"execution_mode": "offline_scaffold"},
                {"execution_mode": "offline_scaffold"}
            )
        )
    finally:
        loop.close()

    assert qa_out["audit_status"] == "OFFLINE_SCAFFOLD"
    assert qa_out["is_payment_eligible"] is False
    assert qa_out["corrections_required"] is True

    # Server-side PayPal order creation & capture MUST reject canonical offline_scaffold
    pay_res = client.post("/api/payments/paypal/create-order", json={"task_id": task_id})
    assert pay_res.status_code == 400
    assert "offline_scaffold" in pay_res.json()["detail"] or "Offline scaffolds are strictly ineligible" in pay_res.json()["detail"]

    cap_res = client.post("/api/payments/paypal/capture-order", json={"task_id": task_id, "order_id": "SIM-ORD-TEST"})
    assert cap_res.status_code == 400
    assert "offline_scaffold" in cap_res.json()["detail"] or "Offline scaffolds are strictly ineligible" in cap_res.json()["detail"]

    # Verify that any arbitrary non-live_ai variant like "scaffold" is also rejected by both endpoints
    from api.database import SessionLocal
    from api.models.task import TaskModel
    db = SessionLocal()
    try:
        scaffold_variant_task = TaskModel(
            user_id="default_user",
            title="Supply Chain Analytics Variant",
            description="Variant test",
            budget=10.0,
            currency="USD",
            status="awaiting_payment",
            execution_plan=json.dumps({"execution_mode": "scaffold"})
        )
        db.add(scaffold_variant_task)
        db.commit()
        db.refresh(scaffold_variant_task)
        var_id = scaffold_variant_task.id

        var_create_res = client.post("/api/payments/paypal/create-order", json={"task_id": var_id})
        assert var_create_res.status_code == 400
        assert "scaffold" in var_create_res.json()["detail"]

        var_cap_res = client.post("/api/payments/paypal/capture-order", json={"task_id": var_id, "order_id": "SIM-ORD-TEST"})
        assert var_cap_res.status_code == 400
        assert "scaffold" in var_cap_res.json()["detail"]
    finally:
        db.close()


def test_paypal_order_creation_rejects_unapproved_or_incomplete_task():
    """Verify server-side positive validation rejects payment creation if QA != APPROVED or steps incomplete."""
    from api.database import SessionLocal
    from api.models.task import TaskModel

    db = SessionLocal()
    try:
        # Create a mock task in database with live_ai mode but awaiting_payment without QA approval
        task = TaskModel(
            user_id="default_user",
            title="Satellite Telecom Market Survey",
            description="LEO constellation analysis.",
            budget=10.0,
            currency="USD",
            status="awaiting_payment",
            execution_plan=json.dumps({"execution_mode": "live_ai", "steps": []})
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

        # Missing steps and missing QA approval -> MUST fail with 400 on create-order
        res = client.post("/api/payments/paypal/create-order", json={"task_id": task_id})
        assert res.status_code == 400
        detail_str = str(res.json()).lower()
        assert "prerequisite" in detail_str or "not completed" in detail_str or "qa" in detail_str

        # Symmetrically MUST fail with 400 on capture-order
        cap_res = client.post("/api/payments/paypal/capture-order", json={"task_id": task_id, "order_id": "SIM-ORD-TEST"})
        assert cap_res.status_code == 400
        cap_detail = str(cap_res.json()).lower()
        assert "prerequisite" in cap_detail or "not completed" in cap_detail or "qa" in cap_detail
    finally:
        db.close()


def test_server_side_paywall_masks_deliverable():
    """Verify that final_output is None and content markdown is masked until task is paid/completed."""
    from api.database import SessionLocal
    from api.models.task import TaskModel, TaskStepModel

    db = SessionLocal()
    try:
        task = TaskModel(
            user_id="default_user",
            title="Robotics Manufacturing Report",
            description="Precision robotics market.",
            budget=10.0,
            currency="USD",
            status="awaiting_payment",
            execution_plan=json.dumps({"execution_mode": "live_ai"})
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # Add content step with secret deliverable markdown
        step = TaskStepModel(
            task_id=task.id,
            step_name="content_generation",
            assigned_agent_id="agent_content_03",
            status="completed",
            output_data=json.dumps({"report_markdown": "# Confirmed Proprietary Robotics Strategy Insights"})
        )
        db.add(step)
        db.commit()

        # Query via API endpoint
        res = client.get(f"/api/tasks/{task.id}")
        assert res.status_code == 200
        data = res.json()

        assert data["final_output"] is None
        content_step = [s for s in data["steps"] if s["step_name"] == "content_generation"][0]
        assert "[PROTECTED DELIVERABLE: Locked pending verified PayPal settlement.]" in content_step["output_data"]["report_markdown"]
        assert "Confirmed Proprietary Robotics Strategy Insights" not in content_step["output_data"]["report_markdown"]

        # Now mark task completed and verify masking is lifted
        task.status = "completed"
        db.commit()

        res_unlocked = client.get(f"/api/tasks/{task.id}")
        assert res_unlocked.status_code == 200
        unlocked_data = res_unlocked.json()
        unlocked_content = [s for s in unlocked_data["steps"] if s["step_name"] == "content_generation"][0]
        assert "Confirmed Proprietary Robotics Strategy Insights" in unlocked_content["output_data"]["report_markdown"]
    finally:
        db.close()


# ==============================================================================
# SECTION 8.7 — SYSTEM STATUS SEMANTICS TESTS
# ==============================================================================

def test_truthful_system_status_semantics():
    """Verify system status truthful semantics across various states."""
    from api.services.llm_provider import ProviderHealthState, LLMProvider

    provider = LLMProvider()

    # 1. When keys are None -> NOT_CONFIGURED
    with patch.object(settings, "GEMINI_API_KEY", None), patch.object(settings, "OPENAI_API_KEY", None):
        assert provider.get_status()["status"] == ProviderHealthState.NOT_CONFIGURED.value

    # 2. When keys are present but unprobed -> CONFIGURED (zero network)
    with patch.object(settings, "GEMINI_API_KEY", "test-key-mock"):
        provider._health_state = ProviderHealthState.CONFIGURED
        assert provider.get_status()["status"] == ProviderHealthState.CONFIGURED.value

    # 3. Quota exhausted -> QUOTA_EXHAUSTED
    provider._health_state = ProviderHealthState.QUOTA_EXHAUSTED
    assert provider.get_status()["status"] == ProviderHealthState.QUOTA_EXHAUSTED.value

    # 4. Service 503 / timeout -> DEGRADED
    provider._health_state = ProviderHealthState.DEGRADED
    assert provider.get_status()["status"] == ProviderHealthState.DEGRADED.value

    # 5. Live success -> HEALTHY
    provider._health_state = ProviderHealthState.HEALTHY
    assert provider.get_status()["status"] == ProviderHealthState.HEALTHY.value


# ==============================================================================
# SECTION 8.8 — RESEARCH EVIDENCE INTEGRITY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_research_evidence_integrity_and_unverified_estimates():
    """Verify that unverified numerical research claims are not classified as empirical facts,
    do not calculate CAGR or charts, source leads remain leads, while genuine user data works."""
    from api.services.agents.data_analysis_agent import DataAnalysisAgent
    from api.services.agents.content_agent import ContentAgent
    from api.services.agents.qa_agent import QualityAssuranceAgent

    # 1. Semiconductor research response with unverified model estimates
    semiconductor_research = {
        "market_overview": "Advanced 3nm/2nm logic foundry market transition to GAA nanosheet architectures.",
        "quantitative_evidence_status": "unverified_estimate",
        "market_size_current": "$140 Billion (Advanced Logic Foundry Segment, 2024 est.)",
        "market_size_forecast": "$230 Billion by 2028",
        "cagr_projected": "13.2%",
        "major_competitors": [
            {
                "name": "TSMC",
                "market_share": "60-65%",
                "share_classification": "unverified_estimate",
                "segment": "Pure-play Foundry"
            },
            {
                "name": "Samsung Foundry",
                "market_share": "10-12%",
                "share_classification": "unverified_estimate",
                "segment": "IDM & Foundry"
            }
        ],
        "growth_drivers": ["AI accelerators", "GAA transitions"],
        "challenges": ["High-NA EUV capital expenditures", "CoWoS packaging bottlenecks"],
        "sources": [
            {
                "source": "TSMC Investor Relations and Earnings Reports",
                "source_classification": "suggested_lead",
                "reliability": "High"
            },
            {
                "source": "SEMI Market Reports",
                "source_classification": "suggested_lead",
                "reliability": "Medium-High"
            }
        ]
    }

    async def mock_agent_llm(prompt, system_instruction=None):
        sys_l = (system_instruction or "").lower()
        if "content synthesis" in sys_l:
            return {
                "executive_summary": "Qualitative overview of advanced foundries.",
                "report_markdown": "# Advanced Semiconductor Foundry\n\nQualitative domain synthesis.",
                "key_takeaways": ["Qualitative synthesis"],
                "strategic_recommendations": ["CapEx monitoring"]
            }
        elif "quality assurance" in sys_l:
            return {
                "audit_status": "NEEDS_REVISION",
                "factual_verification_status": "UNVERIFIED_ESTIMATES",
                "completeness_score": 65,
                "factual_coherence_score": 50,
                "feedback": "Contains unverified estimates."
            }
        return {
            "computed_metrics": {"status": "unverified_estimate"},
            "market_share_breakdown": [],
            "chart_revenue_projections": [],
            "key_findings": ["Unverified estimates"]
        }

    with patch.object(llm_provider, "generate_json", side_effect=mock_agent_llm):
        da = DataAnalysisAgent()
        analysis = await da.execute("Advanced Semiconductor Foundry 3nm/2nm", semiconductor_research)

        # A: Unsupported market sizes are NOT marked verified
        metrics = analysis.get("computed_metrics", {})
        assert metrics.get("status") == "unverified_estimate"
        assert metrics.get("is_verified") is False
        assert metrics.get("base_year_revenue_usd_bn") is None
        assert metrics.get("target_year_revenue_usd_bn") is None

        # B: Unsupported market-share figures are NOT used in quantitative analysis
        assert analysis.get("market_share_breakdown") == []

        # C: Unsupported CAGR inputs do NOT produce calculated charts
        assert metrics.get("cagr_percent") is None
        assert analysis.get("chart_revenue_projections") == []

        # D: Suggested research leads are NOT converted into citations
        sources = semiconductor_research.get("sources", [])
        for s in sources:
            assert s["source_classification"] == "suggested_lead"
            assert "http" not in s.get("source", "").lower()

        # E: Content Agent displays transparent unverified notice and qualitative classification
        ca = ContentAgent()
        content = await ca.execute(
            "Advanced Semiconductor Foundry 3nm/2nm",
            "Analyze 3nm/2nm foundry nodes.",
            semiconductor_research,
            analysis
        )
        report = content.get("report_markdown", "")
        assert "Evidence Notice" in report or "unverified model estimates" in report.lower()
        assert "Verified Autonomous Deliverable" not in report

        # F: QA Agent rejects unverified numerical claims from receiving verified factual approval
        qa = QualityAssuranceAgent()
        qa_audit = await qa.execute(
            "Advanced Semiconductor Foundry 3nm/2nm",
            "Analyze 3nm/2nm foundry nodes.",
            content,
            semiconductor_research,
            analysis
        )
        assert qa_audit.get("audit_status") == "NEEDS_REVISION"
        assert qa_audit.get("factual_verification_status") == "UNVERIFIED_ESTIMATES"
        assert qa_audit.get("is_payment_eligible") is False
        assert qa_audit.get("corrections_required") is True

        # G: Genuine user-provided or appropriately evidenced numerical data continues to work
        verified_research = {
            "market_overview": "Verified electric vehicle fleet analytics.",
            "quantitative_evidence_status": "user_provided",
            "market_size_current": "$3.21B",
            "market_size_forecast": "$113.99B",
            "cagr_projected": "80.79%",
            "major_competitors": [
                {
                    "name": "Tata Motors",
                    "market_share": "70%",
                    "share_classification": "verified",
                    "segment": "Passenger 4W"
                }
            ],
            "growth_drivers": ["FAME subsidies"],
            "challenges": ["Charging infra"],
            "sources": [{"source": "Government Policy Disclosure", "source_classification": "verified_citation"}]
        }
        verified_analysis = await da.execute("EV Market India", verified_research)

        v_metrics = verified_analysis.get("computed_metrics", {})
        assert v_metrics.get("status") == "calculated"
        assert v_metrics.get("is_calculated") is True
        assert v_metrics.get("calculation_status") == "success"
        assert v_metrics.get("is_verified") is False  # Calculations from user benchmarks are NOT externally fact verified
        assert v_metrics.get("cagr_percent") in (80.79, 81.3) or v_metrics.get("cagr_percent") > 40.0
        assert len(verified_analysis.get("chart_revenue_projections", [])) == 7
        assert len(verified_analysis.get("market_share_breakdown", [])) == 1


@pytest.mark.asyncio
async def test_four_evidence_provenance_classifications_distinct():
    """Verify all four evidence classifications (verified_fact, user_provided, unverified_estimate, unavailable)
    remain completely distinct in QA audit status, external verification flag, and payment eligibility."""
    from api.services.agents.qa_agent import QualityAssuranceAgent

    qa = QualityAssuranceAgent()

    async def mock_approved_qa(prompt, system_instruction=None):
        return {
            "audit_status": "APPROVED",
            "completeness_score": 95,
            "factual_coherence_score": 95,
            "constraint_compliance": True,
            "budget_compliance": True,
            "feedback": "Audited successfully.",
            "corrections_required": False
        }

    with patch.object(llm_provider, "generate_json", side_effect=mock_approved_qa):
        # 1. verified_fact: Without an external retrieval engine in the backend, claims of verified_fact fail closed
        qa_verified = await qa.execute(
            "EV Sector",
            "Objective",
            {"report_markdown": "# Empirical Report with Primary Citations\nValid text over 100 characters long."},
            {
                "quantitative_evidence_status": "verified_fact",
                "sources": [{"source": "https://data.gov/ev-stats", "source_classification": "verified_citation"}]
            },
            {"computed_metrics": {"status": "calculated", "is_verified": True}}
        )
        assert qa_verified["audit_status"] == "NEEDS_REVISION"
        assert qa_verified["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
        assert qa_verified["external_verification_performed"] is False
        assert qa_verified["is_payment_eligible"] is False

        # 2. user_provided: user benchmark parameters, NOT externally verified
        qa_user = await qa.execute(
            "EV Sector",
            "Objective",
            {"report_markdown": "# User-Provided Benchmark Report\nValid text over 100 characters long."},
            {"quantitative_evidence_status": "user_provided"},
            {"computed_metrics": {"status": "calculated", "is_calculated": True, "is_verified": False, "cagr_percent": 80.79}}
        )
        assert qa_user["audit_status"] == "APPROVED"
        assert qa_user["factual_verification_status"] == "USER_PROVIDED"
        assert qa_user["external_verification_performed"] is False
        assert qa_user["is_payment_eligible"] is True
        assert "user-provided" in qa_user["verification_disclaimer"].lower()

        # 3. unverified_estimate: model speculative numbers -> rejected
        qa_unverified = await qa.execute(
            "EV Sector",
            "Objective",
            {"report_markdown": "# Speculative Numbers Report\nValid text over 100 characters long."},
            {"quantitative_evidence_status": "unverified_estimate"},
            {"computed_metrics": {"status": "unverified_estimate", "is_verified": False}}
        )
        assert qa_unverified["audit_status"] == "NEEDS_REVISION"
        assert qa_unverified["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
        assert qa_unverified["external_verification_performed"] is False
        assert qa_unverified["is_payment_eligible"] is False

        # 4. unavailable: qualitative AI synthesis -> approved but external_verification is False
        qa_qual = await qa.execute(
            "EV Sector",
            "Objective",
            {"report_markdown": "# Qualitative Domain Analysis\nValid text over 100 characters long."},
            {"quantitative_evidence_status": "unavailable"},
            {"computed_metrics": {"status": "unavailable", "is_verified": False}}
        )
        assert qa_qual["audit_status"] == "APPROVED"
        assert qa_qual["factual_verification_status"] == "QUALITATIVE_SYNTHESIS"
        assert qa_qual["external_verification_performed"] is False
        assert qa_qual["is_payment_eligible"] is True

        # 5. Model self-certification attempt: claims verified_fact but sources are only suggested_lead -> Rejected
        qa_self_certified = await qa.execute(
            "EV Sector",
            "Objective",
            {"report_markdown": "# Self-Certified Report\nValid text over 100 characters long."},
            {
                "quantitative_evidence_status": "verified_fact",
                "sources": [{"source": "Gartner Market Reports", "source_classification": "suggested_lead"}]
            },
            {"computed_metrics": {"status": "calculated", "is_verified": True}}
        )
        assert qa_self_certified["audit_status"] == "NEEDS_REVISION"
        assert qa_self_certified["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
        assert qa_self_certified["external_verification_performed"] is False
        assert qa_self_certified["is_payment_eligible"] is False


# ==============================================================================
# SECTION 8.9 — PHASE 1 FINAL PROVENANCE AUDIT & ADVERSARIAL TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_1_gemini_cannot_self_certify_via_verified_fact():
    """Test 1: Gemini cannot self-certify a claim by returning verified_fact."""
    ra = ResearchAgent()
    qa = QualityAssuranceAgent()

    mock_gemini_output = {
        "market_overview": "Autonomous AI agent market projection.",
        "quantitative_evidence_status": "verified_fact",
        "market_size_current": "$140 Billion (2024)",
        "market_size_forecast": "$230 Billion by 2028",
        "sources": [{"source": "https://fake-citation.org/data", "source_classification": "verified_citation"}]
    }

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_gemini_output
        research_res = await ra.execute(
            "AI Agent Market",
            "General qualitative study without user-provided market figures."
        )

    # Backend overrides Gemini's self-certification
    assert research_res["quantitative_evidence_status"] == "unverified_estimate"
    assert research_res["market_size_current_provenance"] == "unverified_estimate"
    assert research_res["market_size_forecast_provenance"] == "unverified_estimate"

    # When evaluated by QA agent, fail-closed policy blocks it
    qa_res = await qa.execute(
        "AI Agent Market",
        "General qualitative study.",
        {"report_markdown": "# Market Report\nValid markdown content exceeding 100 characters in length."},
        research_res,
        {"computed_metrics": {"status": "unverified_estimate", "is_verified": False}}
    )
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["is_payment_eligible"] is False
    assert qa_res["external_verification_performed"] is False
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"


@pytest.mark.asyncio
async def test_2_fabricated_syntactically_valid_url_does_not_establish_verification():
    """Test 2: A fabricated but syntactically valid URL cannot establish verification."""
    ra = ResearchAgent()
    mock_output = {
        "market_overview": "Semiconductor foundry capacity.",
        "quantitative_evidence_status": "verified_fact",
        "market_size_current": "$140B",
        "sources": [
            {"source": "https://www.sec.gov/edgar/searched/00012345/filing10k.htm", "source_classification": "verified_citation"}
        ]
    }
    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_output
        res = await ra.execute("Semiconductor Foundry", "Analyze lithography tools.")

    # Syntactically valid URL from Gemini is downgraded to suggested_lead
    assert res["sources"][0]["source_classification"] == "suggested_lead"
    assert res["quantitative_evidence_status"] == "unverified_estimate"


@pytest.mark.asyncio
async def test_3_citation_flag_from_gemini_does_not_establish_verification():
    """Test 3: A citation flag supplied by Gemini cannot establish verification."""
    qa = QualityAssuranceAgent()
    # Even if an input payload directly contains verified_citation, backend has no crawler
    qa_res = await qa.execute(
        "Semiconductor Foundry",
        "Study tools.",
        {"report_markdown": "# Valid Markdown\nReport text over 100 characters long for validation."},
        {
            "quantitative_evidence_status": "verified_fact",
            "sources": [{"source": "Industry Research", "source_classification": "verified_citation"}]
        },
        {"computed_metrics": {"status": "calculated", "is_verified": True}}
    )
    assert qa_res["external_verification_performed"] is False
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_4_unretrieved_url_does_not_establish_verification():
    """Test 4: A URL that has not been independently retrieved cannot establish verification."""
    qa = QualityAssuranceAgent()
    qa_res = await qa.execute(
        "Telecom Sector",
        "Assess 5G rollout.",
        {"report_markdown": "# Telecom Report\nValid markdown text exceeding 100 characters."},
        {
            "quantitative_evidence_status": "verified_fact",
            "sources": [{"source": "https://unretrieved-domain.org/stats", "source_classification": "verified_citation"}]
        },
        {"computed_metrics": {"status": "calculated", "is_verified": True}}
    )
    assert qa_res["external_verification_performed"] is False
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"


@pytest.mark.asyncio
async def test_5_source_not_supporting_claim_does_not_establish_verification():
    """Test 5: A source that does not support the specific claim cannot establish verification."""
    qa = QualityAssuranceAgent()
    qa_res = await qa.execute(
        "Aerospace Market",
        "Study propulsion.",
        {"report_markdown": "# Propulsion Report\nValid report content exceeding 100 characters in length."},
        {
            "quantitative_evidence_status": "unverified_estimate",
            "sources": [{"source": "NASA General Homepage", "source_classification": "suggested_lead"}]
        },
        {"computed_metrics": {"status": "unverified_estimate", "is_verified": False}}
    )
    assert qa_res["external_verification_performed"] is False
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_6_prompt_containing_years_or_horizons_does_not_authenticate_estimates():
    """Test 6: A user prompt containing years or forecast periods does not authenticate generated estimates."""
    ra = ResearchAgent()
    prompt_title = "Semiconductor Industry Analysis"
    prompt_desc = "Analyze the semiconductor industry in 2026 and provide a five-year outlook."

    mock_gemini = {
        "market_overview": "Advanced wafer fab equipment.",
        "market_size_current": "$140 Billion (2024)",
        "market_size_forecast": "$230 Billion by 2028",
        "cagr_projected": "13.2%"
    }

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_gemini
        res = await ra.execute(prompt_title, prompt_desc)

    # Prompt contained 2026 and 'five-year', but neither authenticates $140B or $230B
    assert res["quantitative_evidence_status"] == "unverified_estimate"
    assert res["market_size_current_provenance"] == "unverified_estimate"
    assert res["market_size_forecast_provenance"] == "unverified_estimate"


@pytest.mark.asyncio
async def test_7_explicit_user_benchmarks_retain_user_provided_provenance():
    """Test 7: Explicit user-provided benchmark values retain user_provided provenance."""
    ra = ResearchAgent()
    da = DataAnalysisAgent()
    qa = QualityAssuranceAgent()

    title = "EV Market India"
    desc = "Assess EV market growth from $3.21B baseline to $113.99B target over 6 years."

    mock_gemini = {
        "market_overview": "Indian EV expansion.",
        "market_size_current": "$3.21B",
        "market_size_forecast": "$113.99B",
        "cagr_projected": "80.79%"
    }

    async def mock_agent_llm(prompt, system_instruction=None):
        sys_l = (system_instruction or "").lower()
        if "research" in sys_l:
            return mock_gemini
        elif "quality assurance" in sys_l:
            return {
                "audit_status": "APPROVED",
                "completeness_score": 96,
                "factual_coherence_score": 95,
                "constraint_compliance": True,
                "budget_compliance": True,
                "feedback": "Audited user benchmarks successfully.",
                "corrections_required": False
            }
        return {}

    with patch.object(llm_provider, "generate_json", side_effect=mock_agent_llm):
        research_res = await ra.execute(title, desc)

        assert research_res["quantitative_evidence_status"] == "user_provided"
        assert research_res["market_size_current_provenance"] == "user_provided"
        assert research_res["market_size_forecast_provenance"] == "user_provided"

        analysis_res = await da.execute(title, research_res)
        metrics = analysis_res.get("computed_metrics", {})
        assert metrics["status"] == "calculated"
        assert metrics["is_calculated"] is True
        assert metrics["calculation_status"] == "success"
        assert metrics["is_verified"] is False  # Separated from external factual verification
        assert metrics["cagr_percent"] in (80.79, 81.3) or metrics["cagr_percent"] > 40.0
        assert len(analysis_res.get("chart_revenue_projections", [])) == 7

        qa_res = await qa.execute(
            title,
            desc,
            {"report_markdown": "# Valid Benchmark Report\nContent length exceeding 100 characters for testing."},
            research_res,
            analysis_res
        )
        assert qa_res["audit_status"] == "APPROVED"
        assert qa_res["factual_verification_status"] == "USER_PROVIDED"
        assert qa_res["verification_scope"] == "USER_SUPPLIED_BENCHMARK"
        assert qa_res["external_verification_performed"] is False
        assert qa_res["is_payment_eligible"] is True
        assert "user-provided" in qa_res["verification_disclaimer"].lower()


@pytest.mark.asyncio
async def test_8_additional_model_figures_do_not_inherit_user_provided_provenance():
    """Test 8: Additional model-generated figures do not inherit user_provided provenance."""
    ra = ResearchAgent()
    da = DataAnalysisAgent()

    title = "Semiconductor Foundry Baseline"
    desc = "Use a baseline market value of $10 billion in 2024."

    # Model provides user baseline $10B, but invents an unsupported forecast $50B
    mock_gemini = {
        "market_overview": "Semiconductor foundry expansion.",
        "market_size_current": "$10 Billion (2024)",
        "market_size_forecast": "$50 Billion by 2030",
        "cagr_projected": "30.7%"
    }

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_gemini
        research_res = await ra.execute(title, desc)

    # Current is user-provided, but forecast is unverified estimate
    assert research_res["market_size_current_provenance"] == "user_provided"
    assert research_res["market_size_forecast_provenance"] == "unverified_estimate"
    assert research_res["quantitative_evidence_status"] == "unverified_estimate"

    # Data analysis must NOT calculate CAGR or charts with unverified forecast
    analysis_res = await da.execute(title, research_res)
    metrics = analysis_res.get("computed_metrics", {})
    assert metrics["status"] == "unverified_estimate"
    assert metrics["cagr_percent"] is None
    assert analysis_res.get("chart_revenue_projections") == []


@pytest.mark.asyncio
async def test_9_unverified_quantitative_claims_remain_blocked_from_payment_and_charts_empty():
    """Test 9: Unverified quantitative claims remain blocked from payment and cannot populate verified CAGR or projection charts."""
    da = DataAnalysisAgent()
    qa = QualityAssuranceAgent()

    unverified_research = {
        "market_overview": "Unverified projections.",
        "quantitative_evidence_status": "unverified_estimate",
        "market_size_current": "$140B",
        "market_size_forecast": "$230B"
    }

    analysis_res = await da.execute("Unverified Market", unverified_research)
    assert analysis_res.get("chart_revenue_projections") == []
    assert analysis_res.get("computed_metrics", {}).get("cagr_percent") is None

    qa_res = await qa.execute(
        "Unverified Market",
        "Objective",
        {"report_markdown": "# Unverified Report\nValid markdown exceeding 100 characters in length."},
        unverified_research,
        analysis_res
    )
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["is_payment_eligible"] is False
    assert qa_res["external_verification_performed"] is False


@pytest.mark.asyncio
async def test_10_qualitative_synthesis_remains_payable_with_disclosure():
    """Test 10: Qualitative-only synthesis remains payable when the workflow and QA requirements are otherwise satisfied, with the existing disclosure."""
    qa = QualityAssuranceAgent()

    qual_research = {
        "market_overview": "Structural domain qualitative review.",
        "quantitative_evidence_status": "unavailable",
        "sources": [{"source": "SEMI Technical Guidelines", "source_classification": "suggested_lead"}]
    }
    qual_analysis = {
        "computed_metrics": {"status": "unavailable", "is_verified": False},
        "chart_revenue_projections": []
    }
    report = {
        "report_markdown": (
            "# Advanced EUV Lithography Qualitative Briefing\n\n"
            "> **Scope & Evidence Notice**: This deliverable represents qualitative AI intelligence synthesis...\n\n"
            "Technical analysis of high-NA depth of focus and pellicle integrity. Comprehensive review exceeding 100 chars."
        )
    }

    async def mock_approved_audit(prompt, system_instruction=None):
        return {
            "audit_status": "APPROVED",
            "completeness_score": 98,
            "factual_coherence_score": 95,
            "constraint_compliance": True,
            "budget_compliance": True,
            "feedback": "Qualitative synthesis satisfies all requested architectural constraints.",
            "corrections_required": False
        }

    with patch.object(llm_provider, "generate_json", side_effect=mock_approved_audit):
        qa_res = await qa.execute("High-NA Lithography", "Examine depth of focus.", report, qual_research, qual_analysis)

    assert qa_res["audit_status"] == "APPROVED"
    assert qa_res["is_payment_eligible"] is True
    assert qa_res["factual_verification_status"] == "QUALITATIVE_SYNTHESIS"
    assert qa_res["external_verification_performed"] is False
    assert "suggested leads" in qa_res["deliverable_classification"].lower()
    assert "suggested research leads have not been independently fact-verified" in qa_res["verification_disclaimer"].lower()


def test_11_offline_scaffold_and_failed_ai_remain_ineligible_for_payment():
    """Test 11: Offline scaffold and failed AI execution remain ineligible for payment."""
    qa = QualityAssuranceAgent()

    loop = asyncio.new_event_loop()
    try:
        # 1. Offline scaffold rejected by QA
        qa_scaffold = loop.run_until_complete(
            qa.execute(
                "Scaffold Task",
                "Description",
                {"report_markdown": "# Scaffold Report", "execution_mode": "offline_scaffold"},
                {"execution_mode": "offline_scaffold"},
                {"execution_mode": "offline_scaffold"}
            )
        )
        assert qa_scaffold["audit_status"] == "OFFLINE_SCAFFOLD"
        assert qa_scaffold["is_payment_eligible"] is False
        assert qa_scaffold["external_verification_performed"] is False

        # 2. Server-side payment rejection on scaffold
        from api.database import SessionLocal
        from api.models.task import TaskModel
        db = SessionLocal()
        try:
            t = TaskModel(
                user_id="user_test_11",
                title="Test 11 Scaffold",
                description="Scaffold mode test",
                budget=10.0,
                status="awaiting_payment",
                execution_plan=json.dumps({"execution_mode": "offline_scaffold"})
            )
            db.add(t)
            db.commit()
            db.refresh(t)

            res = client.post("/api/payments/paypal/create-order", json={"task_id": t.id})
            assert res.status_code == 400
            assert "offline_scaffold" in res.json()["detail"] or "Offline scaffolds are strictly ineligible" in res.json()["detail"]

            cap_res = client.post("/api/payments/paypal/capture-order", json={"task_id": t.id, "order_id": "SIM-ORD-TEST"})
            assert cap_res.status_code == 400
            assert "offline_scaffold" in cap_res.json()["detail"] or "Offline scaffolds are strictly ineligible" in cap_res.json()["detail"]
        finally:
            db.close()
    finally:
        loop.close()


# ==============================================================================
# SECTION 8.10 — PROVENANCE SEMANTICS & NARRATIVE AUDIT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_user_benchmark_calculation_succeeds_without_factual_verification():
    """Part 1: Prove user benchmark calculations succeed without implying external factual verification."""
    da = DataAnalysisAgent()
    qa = QualityAssuranceAgent()

    user_research = {
        "quantitative_evidence_status": "user_provided",
        "market_size_current": "$3.21B",
        "market_size_forecast": "$113.99B",
        "user_benchmark_evidence": {"baseline": "baseline $3.21B", "forecast": "target $113.99B"}
    }

    async def mock_approved_audit(prompt, system_instruction=None):
        sys_l = (system_instruction or "").lower()
        if "quality assurance" in sys_l:
            return {
                "audit_status": "APPROVED",
                "completeness_score": 96,
                "factual_coherence_score": 95,
                "constraint_compliance": True,
                "budget_compliance": True,
                "feedback": "User benchmarks validated.",
                "corrections_required": False
            }
        return {}

    with patch.object(llm_provider, "generate_json", side_effect=mock_approved_audit):
        analysis_res = await da.execute("EV Market India", user_research)
        metrics = analysis_res.get("computed_metrics", {})

        # 1. Calculation completed successfully
        assert metrics.get("status") == "calculated"
        assert metrics.get("is_calculated") is True
        assert metrics.get("calculation_status") == "success"
        assert metrics.get("cagr_percent") in (80.79, 81.3) or metrics.get("cagr_percent") > 40.0
        assert len(analysis_res.get("chart_revenue_projections", [])) == 7

        # 2. External factual verification remains strictly false
        assert metrics.get("is_verified") is False
        assert metrics.get("provenance") == "user_provided"

        qa_res = await qa.execute(
            "EV Market India",
            "Study EV growth from baseline $3.21B to target $113.99B.",
            {"report_markdown": "# Valid Benchmark Deliverable\nContent exceeding 100 characters in length."},
            user_research,
            analysis_res
        )

    # 3. Deliverable remains labelled as user-provided
    assert qa_res["audit_status"] == "APPROVED"
    assert qa_res["is_payment_eligible"] is True
    assert qa_res["factual_verification_status"] == "USER_PROVIDED"
    assert qa_res["deliverable_classification"] == "User-Provided Benchmark Analysis"
    assert qa_res["external_verification_performed"] is False
    assert "not independently fact-verified by external primary records" in qa_res["verification_disclaimer"].lower()


@pytest.mark.asyncio
async def test_unrelated_monetary_amounts_in_prompt_rejected_as_benchmarks():
    """Part 2: Unrelated prompt references (e.g. $10B budget, $50B acquisition) cannot become market benchmarks."""
    ra = ResearchAgent()
    title = "Quantum Computing Market Study"
    desc = "The project has a budget of $10 billion and an acquisition target of $50 billion. Provide a market study of quantum computing."

    # Gemini tries to reuse $10B and $50B as current and forecast market sizes
    mock_gemini = {
        "market_overview": "Quantum hardware market overview.",
        "market_size_current": "$10 Billion (2024)",
        "market_size_forecast": "$50 Billion by 2030",
        "cagr_projected": "30.7%"
    }

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_gemini
        research_res = await ra.execute(title, desc)

    # Both unrelated numbers must be rejected from receiving user_provided provenance
    assert research_res["market_size_current_provenance"] == "unverified_estimate"
    assert research_res["market_size_forecast_provenance"] == "unverified_estimate"
    assert research_res["quantitative_evidence_status"] == "unverified_estimate"


@pytest.mark.asyncio
async def test_ambiguous_monetary_values_fail_closed():
    """Part 2: Ambiguous monetary values without a clear market sizing role fail closed."""
    ra = ResearchAgent()
    title = "SaaS Analytics Market"
    desc = "We spent $5M on R&D and revenue was $20M last quarter. Provide market analysis."

    mock_gemini = {
        "market_overview": "SaaS analytics segment.",
        "market_size_current": "$5 Million",
        "market_size_forecast": "$20 Million",
        "cagr_projected": "25.0%"
    }

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_gemini
        research_res = await ra.execute(title, desc)

    # R&D spend and quarterly revenue must fail closed
    assert research_res["market_size_current_provenance"] == "unverified_estimate"
    assert research_res["market_size_forecast_provenance"] == "unverified_estimate"
    assert research_res["quantitative_evidence_status"] == "unverified_estimate"


@pytest.mark.asyncio
async def test_narrative_claim_in_research_summary_blocked_by_qa():
    """Part 3: Quantitative market claims hidden in market_overview are caught and blocked."""
    qa = QualityAssuranceAgent()

    # Model leaves structured fields empty/unavailable to evade the gate
    research_with_narrative = {
        "quantitative_evidence_status": "unavailable",
        "market_size_current": None,
        "market_size_forecast": None,
        "market_overview": "The advanced EUV lithography market is currently valued at $140 billion and will reach $230 billion by 2028 with a 13.2% CAGR."
    }
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}
    report = {"report_markdown": "# Qualitative Briefing\nReviewing EUV technical optics with content over 100 characters."}

    qa_res = await qa.execute("EUV Lithography", "Examine EUV optics.", report, research_with_narrative, analysis)

    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False
    assert qa_res["external_verification_performed"] is False
    assert "narrative content without empirical citations" in qa_res["feedback"].lower()


@pytest.mark.asyncio
async def test_narrative_claim_in_key_findings_blocked_by_qa():
    """Part 3: Quantitative market share claim hidden in key_findings is caught and blocked."""
    qa = QualityAssuranceAgent()

    research = {
        "quantitative_evidence_status": "unavailable",
        "market_size_current": None,
        "market_size_forecast": None,
        "market_overview": "Foundry technology review."
    }
    analysis = {
        "computed_metrics": {"status": "unavailable", "is_verified": False},
        "key_findings": ["TSMC commands a 65% market share in leading-edge logic foundry capacity."]
    }
    report = {"report_markdown": "# Qualitative Briefing\nReviewing foundry tech with content over 100 characters."}

    qa_res = await qa.execute("Foundry Technology", "Review foundry nodes.", report, research, analysis)

    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_narrative_claim_in_executive_synthesis_blocked_by_qa():
    """Part 3: Quantitative market sizing claim hidden in report_markdown is caught and blocked."""
    qa = QualityAssuranceAgent()

    research = {"quantitative_evidence_status": "unavailable"}
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}
    report = {
        "report_markdown": (
            "# Advanced Semiconductor Synthesis\n\n"
            "Valued at $140 billion in 2024, the advanced logic market is projected to reach $230 billion.\n"
            "Technical outline of GAA nanosheets with comprehensive text exceeding 100 characters."
        )
    }

    qa_res = await qa.execute("Advanced GAA", "Study GAA nanosheets.", report, research, analysis)

    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_narrative_claim_in_recommendations_blocked_by_qa():
    """Part 3: Quantitative market sizing claim hidden in strategic_recommendations is caught and blocked."""
    qa = QualityAssuranceAgent()

    research = {"quantitative_evidence_status": "unavailable"}
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}
    report = {
        "report_markdown": "# GAA Architecture\nComprehensive technical synthesis text exceeding 100 characters.",
        "strategic_recommendations": [
            "Capture 15% market share of the $230 billion market opportunity by 2028."
        ]
    }

    qa_res = await qa.execute("GAA Architecture", "Study GAA nanosheets.", report, research, analysis)

    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_clean_qualitative_synthesis_with_dates_and_specs_approved():
    """Part 3: Clean qualitative text with dates, specs, and counts is not falsely flagged."""
    qa = QualityAssuranceAgent()

    research = {
        "quantitative_evidence_status": "unavailable",
        "market_overview": "High-NA EUV lithography increases numerical aperture to 0.55 NA from 0.33 NA, utilizing 13.5nm wavelength.",
        "challenges": ["Pellicle heating under 500W source power", "Optics contamination", "Line-edge roughness"]
    }
    analysis = {
        "computed_metrics": {"status": "unavailable", "is_verified": False},
        "key_findings": ["Three key technical bottlenecks identify optics degradation as primary operational concern."]
    }
    report = {
        "report_markdown": (
            "# High-NA EUV Lithography Architecture\n\n"
            "> **Scope & Evidence Notice**: This deliverable represents qualitative AI intelligence synthesis...\n\n"
            "High-NA EUV lithography deploys 0.55 NA anamorphic optics for 2nm logic nodes. "
            "A 5-year deployment cycle starting in 2026 will transition foundries to hyper-NA. "
            "Exhaustive engineering analysis with valid text well exceeding 100 characters in length."
        )
    }

    async def mock_approved_audit(prompt, system_instruction=None):
        return {
            "audit_status": "APPROVED",
            "completeness_score": 98,
            "factual_coherence_score": 96,
            "constraint_compliance": True,
            "budget_compliance": True,
            "feedback": "Exhaustive qualitative synthesis satisfies all requested architectural constraints.",
            "corrections_required": False
        }

    with patch.object(llm_provider, "generate_json", side_effect=mock_approved_audit):
        qa_res = await qa.execute("High-NA EUV", "Examine EUV deployment.", report, research, analysis)

    assert qa_res["audit_status"] == "APPROVED"
    assert qa_res["is_payment_eligible"] is True
    assert qa_res["factual_verification_status"] == "QUALITATIVE_SYNTHESIS"
    assert qa_res["external_verification_performed"] is False
    assert qa_res["deliverable_classification"] == "Qualitative AI Synthesis (Suggested Leads Only, Not Independently Verified)"


# ==============================================================================
# SECTION 8.11 — EXPANDED NARRATIVE CLAIM CATEGORIES & ROLE-AWARE WHITELISTING
# ==============================================================================

@pytest.mark.asyncio
async def test_narrative_claim_revenue_growth_percentage_blocked():
    """Verify revenue growth percentages in narrative text are caught and blocked."""
    qa = QualityAssuranceAgent()
    research = {"quantitative_evidence_status": "unavailable"}
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}
    report = {
        "report_markdown": "# Market Outlook\nRevenue will increase by 35% over the next cycle with strong performance."
    }
    qa_res = await qa.execute("SaaS Sector", "Evaluate SaaS.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_narrative_claim_ev_adoption_rate_blocked():
    """Verify adoption rate claims in narrative text are caught and blocked."""
    qa = QualityAssuranceAgent()
    research = {"quantitative_evidence_status": "unavailable"}
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}
    report = {
        "report_markdown": "# Clean Energy Roadmap\nEV adoption will reach 40% by 2030 across major urban metropolitan areas."
    }
    qa_res = await qa.execute("Clean Energy", "Study EV.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_narrative_claim_annual_shipment_volume_blocked():
    """Verify physical shipment volume projections in narrative text are caught and blocked."""
    qa = QualityAssuranceAgent()
    research = {"quantitative_evidence_status": "unavailable"}
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}
    report = {
        "report_markdown": "# Device Logistics\nAnnual shipments will reach 2 million units across all global distribution channels."
    }
    qa_res = await qa.execute("Logistics", "Study shipments.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_narrative_claim_operating_margin_improvement_blocked():
    """Verify financial margin expansion claims in narrative text are caught and blocked."""
    qa = QualityAssuranceAgent()
    research = {"quantitative_evidence_status": "unavailable"}
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}
    report = {
        "report_markdown": "# Profitability Assessment\nOperating margin will improve by 8 percentage points through supply efficiency."
    }
    qa_res = await qa.execute("Profitability", "Assess margins.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_narrative_claim_annual_sales_forecast_blocked():
    """Verify sales revenue forecasts in narrative text are caught and blocked."""
    qa = QualityAssuranceAgent()
    research = {"quantitative_evidence_status": "unavailable"}
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}
    report = {
        "report_markdown": "# Commercial Forecast\nAnnual sales will reach $5 billion as commercial rollout accelerates."
    }
    qa_res = await qa.execute("Commercial", "Forecast sales.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_narrative_claim_customer_growth_blocked():
    """Verify customer acquisition / subscriber count claims in narrative text are caught and blocked."""
    qa = QualityAssuranceAgent()
    research = {"quantitative_evidence_status": "unavailable"}
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}
    report = {
        "report_markdown": "# Subscriber Growth\nThe sector will add 3 million customers during the initial commercialization phase."
    }
    qa_res = await qa.execute("Subscriber Sector", "Study users.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_role_aware_user_benchmarks_whitelisted_only_in_market_sizing_role():
    """Verify authorized user benchmarks ($10B baseline, $20B forecast, 12.25% CAGR) pass in market sizing context."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "user_provided",
        "market_size_current": "$10B",
        "market_size_forecast": "$20B",
        "user_benchmark_evidence": {"baseline": "baseline $10B", "forecast": "forecast $20B"}
    }
    analysis = {
        "computed_metrics": {
            "status": "calculated",
            "is_calculated": True,
            "calculation_status": "success",
            "is_verified": False,
            "cagr_percent": 12.25
        }
    }
    report = {
        "report_markdown": (
            "# Strategic Market Benchmark Assessment\n\n"
            "Based on user-provided benchmarks, the current market baseline is $10B in 2024, "
            "projected to reach a forecast of $20B by 2030 at a calculated CAGR of 12.25%. "
            "Exhaustive analysis with report length well over one hundred characters."
        )
    }

    async def mock_approved_audit(prompt, system_instruction=None):
        return {
            "audit_status": "APPROVED",
            "completeness_score": 98,
            "factual_coherence_score": 96,
            "constraint_compliance": True,
            "budget_compliance": True,
            "feedback": "Approved benchmarks validated.",
            "corrections_required": False
        }

    with patch.object(llm_provider, "generate_json", side_effect=mock_approved_audit):
        qa_res = await qa.execute("Semiconductor Fab", "Baseline $10B to forecast $20B.", report, research, analysis)

    assert qa_res["audit_status"] == "APPROVED"
    assert qa_res["is_payment_eligible"] is True
    assert qa_res["factual_verification_status"] == "USER_PROVIDED"


@pytest.mark.asyncio
async def test_role_aware_benchmark_number_cannot_authorize_unrelated_claim():
    """Verify approved benchmark numbers (10, 20) cannot authorize 10% market share or 20% margin."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "user_provided",
        "market_size_current": "$10B",
        "market_size_forecast": "$20B"
    }
    analysis = {
        "computed_metrics": {
            "status": "calculated",
            "is_calculated": True,
            "cagr_percent": 12.25
        }
    }
    report = {
        "report_markdown": (
            "# Benchmark Report\n"
            "The baseline is $10B and forecast is $20B. "
            "Intel will hold a 10% market share and operating margin will reach 20%."
        )
    }
    qa_res = await qa.execute("Semiconductor Fab", "Baseline $10B to forecast $20B.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_model_injected_number_alongside_user_benchmarks_fails_closed():
    """Verify an invented third number ($30B) fails closed even when user benchmarks are present."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "user_provided",
        "market_size_current": "$10B",
        "market_size_forecast": "$20B"
    }
    analysis = {
        "computed_metrics": {
            "status": "calculated",
            "is_calculated": True,
            "cagr_percent": 12.25
        }
    }
    report = {
        "report_markdown": (
            "# Benchmark Report\n"
            "The baseline is $10B and forecast is $20B. "
            "However, TSMC alone will hit $30B valuation by the end of the forecast period."
        )
    }
    qa_res = await qa.execute("Semiconductor Fab", "Baseline $10B to forecast $20B.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_unrelated_company_sales_using_benchmark_number_blocked():
    """Verify approved benchmark number ($10B) cannot be attributed as company sales."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "user_provided",
        "market_size_current": "$10B",
        "market_size_forecast": "$20B"
    }
    analysis = {
        "computed_metrics": {
            "status": "calculated",
            "is_calculated": True,
            "cagr_percent": 12.25
        }
    }
    report = {
        "report_markdown": (
            "# Benchmark Report\n"
            "Current baseline market is $10B, forecast is $20B. "
            "In addition, TSMC will achieve annual sales of $10 billion."
        )
    }
    qa_res = await qa.execute("Semiconductor Fab", "Baseline $10B to forecast $20B.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_narrative_claim_hidden_in_source_notes_or_competitor_segment_blocked():
    """Verify narrative quantitative claims hidden in sources.notes or competitors are caught."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "unavailable",
        "sources": [
            {
                "source": "Gartner Special Report",
                "source_classification": "suggested_lead",
                "notes": "Research note predicts annual sales will reach $5 billion by 2028."
            }
        ]
    }
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}
    report = {
        "report_markdown": "# GAA Architecture\nExhaustive technical synthesis text exceeding 100 characters in length."
    }
    qa_res = await qa.execute("GAA Architecture", "Study GAA nanosheets.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


# ==============================================================================
# SECTION 8.12 — STRUCTURED METRIC & PERFORMANCE CLAIM AUDIT
# ==============================================================================

@pytest.mark.asyncio
async def test_market_share_breakdown_adversarial_case1_unsupported_shares_blocked():
    """Case 1: Gemini supplies 60%, 25%, 15% market shares without supporting evidence -> Blocked."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "unverified_estimate",
        "market_size_current": "$140B",
        "market_size_forecast": "$230B"
    }
    analysis = {
        "computed_metrics": {"status": "unverified_estimate", "is_verified": False},
        "market_share_breakdown": [
            {"label": "TSMC", "value": 60.0, "category": "Foundry"},
            {"label": "Samsung", "value": 25.0, "category": "Foundry"},
            {"label": "Intel", "value": 15.0, "category": "Foundry"}
        ]
    }
    report = {
        "report_markdown": "# Semiconductor Foundry Overview\nDetailed technical analysis of foundry manufacturing."
    }
    qa_res = await qa.execute("Foundry Survey", "Survey advanced foundries.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False


@pytest.mark.asyncio
async def test_market_share_breakdown_adversarial_case2_breakdown_with_empty_market_size_blocked():
    """Case 2: Gemini supplies market share breakdown while market size is empty -> Blocked."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "unavailable",
        "market_size_current": None,
        "market_size_forecast": None
    }
    analysis = {
        "computed_metrics": {"status": "unavailable", "is_verified": False},
        "market_share_breakdown": [
            {"label": "TSMC", "value": 60.0, "category": "Foundry"},
            {"label": "Samsung", "value": 25.0, "category": "Foundry"},
            {"label": "Intel", "value": 15.0, "category": "Foundry"}
        ]
    }
    report = {
        "report_markdown": "# Qualitative Foundry Analysis\nDetailed overview of lithography and yield ramp operations."
    }
    qa_res = await qa.execute("Foundry Analysis", "Analyze qualitative foundry landscape.", report, research, analysis)
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False
    assert "Unsupported model-generated market share" in qa_res["feedback"]


@pytest.mark.asyncio
async def test_market_share_breakdown_adversarial_case3_user_market_size_does_not_authorize_competitor_shares():
    """Case 3: User provides market size ($10B/$20B), but Gemini invents competitor shares -> Blocked."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "user_provided",
        "market_size_current": "$10B",
        "market_size_forecast": "$20B",
        "user_benchmark_evidence": {
            "baseline": "baseline $10B",
            "forecast": "target $20B"
        }
    }
    analysis = {
        "computed_metrics": {
            "status": "calculated",
            "is_calculated": True,
            "cagr_percent": 14.87
        },
        "market_share_breakdown": [
            {"label": "TSMC", "value": 60.0, "category": "Foundry"},
            {"label": "Samsung", "value": 25.0, "category": "Foundry"},
            {"label": "Intel", "value": 15.0, "category": "Foundry"}
        ]
    }
    report = {
        "report_markdown": "# Benchmark Analysis\nBaseline is $10B and projected target is $20B with calculated CAGR."
    }
    qa_res = await qa.execute(
        "Foundry Sizing",
        "Analyze market growth from baseline $10B to forecast $20B.",
        report,
        research,
        analysis
    )
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False
    assert "Unsupported model-generated market share" in qa_res["feedback"]


@pytest.mark.asyncio
async def test_market_share_breakdown_adversarial_case4_inconsistent_sum_exceeding_100_percent_blocked():
    """Case 4: Breakdown percentages sum to >100% (e.g. 115%) -> Blocked."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "user_provided",
        "market_size_current": "$10B",
        "market_size_forecast": "$20B",
        "user_benchmark_evidence": {
            "competitor_shares": {"tsmc": 60.0, "samsung": 25.0, "intel": 30.0}
        }
    }
    analysis = {
        "computed_metrics": {"status": "calculated", "is_calculated": True, "cagr_percent": 14.87},
        "market_share_breakdown": [
            {"label": "TSMC", "value": 60.0, "category": "Foundry"},
            {"label": "Samsung", "value": 25.0, "category": "Foundry"},
            {"label": "Intel", "value": 30.0, "category": "Foundry"}
        ]
    }
    report = {
        "report_markdown": "# Benchmark Analysis\nBaseline is $10B and target is $20B with competitor shares."
    }
    qa_res = await qa.execute(
        "Foundry Allocation",
        "TSMC 60% share, Samsung 25% share, Intel 30% share.",
        report,
        research,
        analysis
    )
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False
    assert "exceeding 100%" in qa_res["feedback"]


@pytest.mark.asyncio
async def test_market_share_breakdown_adversarial_case5_unsupported_segment_shares_blocked():
    """Case 5: Breakdown with unsupported segment shares -> Blocked."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "user_provided",
        "market_size_current": "$10B",
        "market_size_forecast": "$20B",
        "user_benchmark_evidence": {
            "baseline": "baseline $10B",
            "forecast": "target $20B"
        }
    }
    analysis = {
        "computed_metrics": {"status": "calculated", "is_calculated": True, "cagr_percent": 14.87},
        "market_share_breakdown": [
            {"label": "TSMC", "value": 65.0, "category": "Advanced 3nm Segment"}
        ]
    }
    report = {
        "report_markdown": "# Advanced Segment Analysis\nBaseline is $10B and target is $20B."
    }
    qa_res = await qa.execute(
        "Segment Sizing",
        "Analyze baseline $10B to forecast $20B.",
        report,
        research,
        analysis
    )
    assert qa_res["audit_status"] == "NEEDS_REVISION"
    assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
    assert qa_res["is_payment_eligible"] is False
    assert "Unsupported model-generated market share" in qa_res["feedback"]


@pytest.mark.asyncio
async def test_unsupported_performance_and_sla_claims_detected_and_blocked():
    """Verify operational performance, SLA, latency, and concurrency claims fail closed."""
    qa = QualityAssuranceAgent()
    research = {"quantitative_evidence_status": "unavailable"}
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}

    perf_cases = [
        "The platform guarantees 99.9% uptime across all cloud regions.",
        "The service achieved 99.99% uptime last year during peak trading.",
        "Latency improved by 40% following the optimization sprint.",
        "Processing speed increased by 3x after moving to parallel pipelines.",
        "The system supports 10,000 concurrent users under full load."
    ]

    for claim_text in perf_cases:
        report = {
            "report_markdown": f"# Operational Performance Report\n{claim_text}\nComprehensive technical review."
        }
        qa_res = await qa.execute("Performance Review", "Review platform performance.", report, research, analysis)
        assert qa_res["audit_status"] == "NEEDS_REVISION", f"Expected rejection for '{claim_text}', got {qa_res['audit_status']}"
        assert qa_res["factual_verification_status"] == "UNVERIFIED_ESTIMATES"
        assert qa_res["is_payment_eligible"] is False
        assert "unsupported quantitative claims" in qa_res["feedback"].lower()


@pytest.mark.asyncio
async def test_physical_specifications_preserved_without_false_positives():
    """Verify physical hardware specifications (13.5nm, 0.55 NA, 500W, 300mm, 2nm) pass cleanly."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "unavailable",
        "suggested_leads": ["ASML Technical Whitepapers", "IEEE Lithography Transactions"]
    }
    analysis = {"computed_metrics": {"status": "unavailable", "is_verified": False}}
    report = {
        "report_markdown": (
            "# Advanced Lithography Architecture Review\n\n"
            "High-NA EUV lithography employs a 13.5nm wavelength light source combined with a 0.55 NA lens system. "
            "The extreme ultraviolet plasma source operates at 500W power to sustain high throughput across standard "
            "300mm silicon wafers. The industry 2nm node logic roadmap targets production introduction over a multi-year horizon."
        )
    }

    mock_llm_qa = {
        "audit_status": "APPROVED",
        "completeness_score": 95,
        "factual_coherence_score": 90,
        "constraint_compliance": True,
        "budget_compliance": True,
        "feedback": "Comprehensive technical architecture review meeting qualitative specifications.",
        "corrections_required": False
    }

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_qa
        qa_res = await qa.execute(
            "High-NA Lithography Review",
            "Examine physical parameters of High-NA EUV systems.",
            report,
            research,
            analysis
        )

    assert qa_res["audit_status"] == "APPROVED"
    assert qa_res["is_payment_eligible"] is True
    assert qa_res["factual_verification_status"] == "QUALITATIVE_SYNTHESIS"
    assert qa_res["external_verification_performed"] is False
    assert "Qualitative AI Synthesis" in qa_res["deliverable_classification"]


@pytest.mark.asyncio
async def test_legitimate_user_provided_competitor_share_authorized():
    """Verify user-provided competitor market shares (e.g. Tata Motors 70%) are authorized and pass validation."""
    qa = QualityAssuranceAgent()
    research = {
        "quantitative_evidence_status": "user_provided",
        "user_benchmark_evidence": {
            "competitor_shares": {"tata motors": 70.0}
        }
    }
    analysis = {
        "computed_metrics": {"status": "unavailable", "is_verified": False},
        "market_share_breakdown": [
            {"label": "Tata Motors", "value": 70.0, "category": "Passenger EV"}
        ]
    }
    report = {
        "report_markdown": "# Indian EV Market Analysis\nTata Motors holds 70% share in the passenger EV segment as provided."
    }

    mock_llm_qa = {
        "audit_status": "APPROVED",
        "completeness_score": 92,
        "factual_coherence_score": 88,
        "constraint_compliance": True,
        "budget_compliance": True,
        "feedback": "User-supplied competitor share correctly analyzed.",
        "corrections_required": False
    }

    with patch.object(llm_provider, "generate_json", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_llm_qa
        qa_res = await qa.execute(
            "Indian EV Analysis",
            "Analyze EV market with Tata Motors 70% share.",
            report,
            research,
            analysis
        )

    assert qa_res["audit_status"] == "APPROVED"
    assert qa_res["is_payment_eligible"] is True
