from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.services.llm_provider import llm_provider
from api.services.paypal_service import paypal_service

client = TestClient(app)


def test_full_autonomous_agent_workflow():
    async def mock_generate_json(prompt, system_instruction=None):
        sys_lower = (system_instruction or "").lower()

        if "orchestrator" in sys_lower:
            return {
                "objective_summary": "Comprehensive analysis of India's electric vehicle market.",
                "complexity_tier": "Standard",
                "estimated_total_cost": 8.00,
                "execution_mode": "live_ai",
                "subtasks": [
                    {"subtask_id": "subtask_01", "assigned_agent_id": "agent_research_01", "title": "Market Research", "estimated_cost": 2.0},
                    {"subtask_id": "subtask_02", "assigned_agent_id": "agent_analysis_02", "title": "Data Analysis", "estimated_cost": 3.0},
                    {"subtask_id": "subtask_03", "assigned_agent_id": "agent_content_03", "title": "Content Generation", "estimated_cost": 2.0},
                    {"subtask_id": "subtask_04", "assigned_agent_id": "agent_qa_04", "title": "Quality Assurance", "estimated_cost": 1.0}
                ]
            }
        elif "research agent" in sys_lower:
            return {
                "market_size_current": "$3.21B",
                "market_size_forecast": "$113.99B",
                "forecast_period": "2024-2030",
                "cagr_percent": 80.79,
                "key_drivers": ["FAME-II subsidy policy", "Battery gigafactory investments"],
                "major_competitors": [
                    {"name": "Tata Motors", "segment": "Passenger 4W"},
                    {"name": "Ola Electric", "segment": "2W"}
                ],
                "challenges": ["Charging infrastructure", "High battery costs"]
            }
        elif "data analysis" in sys_lower:
            return {
                "computed_metrics": {
                    "base_year_revenue_usd_bn": 3.21,
                    "target_year_revenue_usd_bn": 113.99,
                    "cagr_percent": 80.79,
                    "period_years": 6,
                    "status": "calculated"
                },
                "market_share_breakdown": [],
                "key_findings": ["CAGR of 80.79% calculated from 2024 to 2030."]
            }
        elif "content synthesis" in sys_lower:
            return {
                "executive_summary": "Comprehensive analysis of India's electric vehicle industry.",
                "report_markdown": "# Electric Vehicle Market Research Report India\n\n## Market Overview\nThe Indian EV market was valued at $3.21B in 2024 and is projected to reach $113.99B by 2030, representing a CAGR of 80.79%.\n\n## Competitor Landscape\n- Tata Motors leads passenger EV market segment.\n- Ola Electric leads 2-wheeler segment.\n\n## Strategic Recommendations\n1. Expand charging infrastructure.",
                "key_takeaways": ["80.79% CAGR expected", "Tata Motors dominates passenger segment"],
                "strategic_recommendations": ["Accelerate fast charging network rollout"]
            }
        elif "quality assurance" in sys_lower:
            return {
                "audit_status": "APPROVED",
                "completeness_score": 96,
                "factual_coherence_score": 95,
                "constraint_compliance": True,
                "budget_compliance": True,
                "feedback": "Deliverable satisfies all requirements with verified empirical CAGR of 80.79% and comprehensive competitor analysis.",
                "corrections_required": False,
                "is_payment_eligible": True
            }
        return {}

    with patch.object(llm_provider, "generate_json", side_effect=mock_generate_json):
        # STEP 1: User Request
        task_res = client.post("/api/tasks", json={
            "title": "Electric Vehicle Market Research Report India",
            "description": "Create a detailed market research report about the electric vehicle industry in India based on baseline $3.21B and target $113.99B benchmark data. Include market size, major competitors, future trends, opportunities, and a final investment analysis. My maximum budget is $10.",
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

        # STEP 8: Create PayPal Order (mocked to prevent live sandbox order pollution)
        mock_order = {
            "order_id": f"TEST-ORD-{task_id[:8]}",
            "status": "CREATED",
            "approval_url": f"https://www.sandbox.paypal.com/checkoutnow?token=TEST-ORD-{task_id[:8]}"
        }
        with patch.object(paypal_service, "create_order", new_callable=AsyncMock) as mock_co:
            mock_co.return_value = mock_order
            order_res = client.post("/api/payments/paypal/create-order", json={"task_id": task_id})
            assert order_res.status_code == 200, f"create-order failed: {order_res.json()}"
            order_data = order_res.json()
            order_id = order_data["order_id"]

        # STEP 9: User Authorizes & Backend Captures Payment (via test simulated order)
        sim_id = f"SIM-ORD-{task_id[:8]}"
        capture_res = client.post("/api/payments/paypal/capture-order", json={
            "task_id": task_id,
            "order_id": sim_id
        })
        assert capture_res.status_code == 200
        cap_data = capture_res.json()
        assert cap_data["success"] is True

        # Advance final delivery step
        adv_res = client.post(f"/api/tasks/{task_id}/advance")
        assert adv_res.status_code == 200

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
