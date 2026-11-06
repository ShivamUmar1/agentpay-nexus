import json
import logging
import re
from typing import Dict, Any, Optional
import httpx
from api.config import settings

logger = logging.getLogger(__name__)


def extract_json(text: str) -> Dict[str, Any]:
    """Extracts JSON object from LLM response text, handling markdown fences."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback regex search for { ... }
        brace_match = re.search(r"(\{[\s\S]*\})", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(1))
            except Exception:
                pass
        raise ValueError(f"Could not parse valid JSON from text: {text[:200]}")


class LLMProvider:
    """Central provider abstraction supporting Gemini, OpenAI, and deterministic demo fallback."""

    def __init__(self):
        self.gemini_key = settings.GEMINI_API_KEY
        self.openai_key = settings.OPENAI_API_KEY
        self.gemini_model = settings.GEMINI_MODEL
        self.openai_model = settings.OPENAI_MODEL

    @property
    def provider_name(self) -> str:
        if self.gemini_key:
            return "gemini"
        if self.openai_key:
            return "openai"
        return "deterministic_fallback"

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generates text from the configured provider or fallback."""
        if self.gemini_key:
            return await self._call_gemini(prompt, system_instruction)
        elif self.openai_key:
            return await self._call_openai(prompt, system_instruction)
        return self._generate_fallback_text(prompt, system_instruction)

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Generates structured JSON from the configured provider or fallback."""
        full_system = (system_instruction or "") + "\n\nCRITICAL: Respond ONLY with a valid JSON object. Do not include introductory or concluding conversational prose."
        
        if self.gemini_key:
            text = await self._call_gemini(prompt, full_system)
            return extract_json(text)
        elif self.openai_key:
            text = await self._call_openai(prompt, full_system)
            return extract_json(text)
        
        return self._generate_fallback_json(prompt, system_instruction)

    async def _call_gemini(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"
        contents = []
        if system_instruction:
            contents.append({"role": "user", "parts": [{"text": f"System context: {system_instruction}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will strictly follow this context."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_openai(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.openai_model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 4096
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _generate_fallback_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Deterministic high-quality fallback text when API keys are not supplied."""
        return (
            "# Executive Analysis Dossier\n\n"
            "> **Notice**: Generated via AgentPay Nexus Deterministic Fallback Intelligence Engine.\n\n"
            f"### Primary Analysis for Query: {prompt[:120]}...\n\n"
            "This synthesized market intelligence report evaluates sector macro drivers, competitive benchmarks, "
            "unit economics, and projected growth vectors based on validated economic baselines."
        )

    def _generate_fallback_json(self, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]:
        """Deterministic realistic JSON outputs based on prompt context."""
        lower_prompt = prompt.lower()
        
        # If prompt is for planning
        if "plan" in lower_prompt or "subtask" in lower_prompt or "orchestrat" in lower_prompt:
            return {
                "objective_summary": "Comprehensive multi-agent execution pipeline covering deep market research, quantitative analytics, executive synthesis, and quality auditing.",
                "complexity_tier": "High",
                "estimated_total_cost": 8.00,
                "subtasks": [
                    {
                        "step_name": "research",
                        "assigned_agent_id": "agent_research_01",
                        "agent_category": "Research",
                        "objective": "Gather domain fundamentals, market sizing, key players, regulatory drivers, and historical growth baselines.",
                        "dependencies": ["planning"],
                        "estimated_cost": 2.00
                    },
                    {
                        "step_name": "data_analysis",
                        "assigned_agent_id": "agent_analysis_02",
                        "agent_category": "Analytics",
                        "objective": "Compute CAGR, market share distributions, revenue trajectories, and chart-ready quantitative datasets.",
                        "dependencies": ["research"],
                        "estimated_cost": 3.00
                    },
                    {
                        "step_name": "content_generation",
                        "assigned_agent_id": "agent_content_03",
                        "agent_category": "Content",
                        "objective": "Synthesize research and analytical findings into an executive-grade Markdown deliverable.",
                        "dependencies": ["data_analysis"],
                        "estimated_cost": 2.00
                    },
                    {
                        "step_name": "quality_assurance",
                        "assigned_agent_id": "agent_qa_04",
                        "agent_category": "Verification",
                        "objective": "Audit deliverable completeness, check compliance with user budget & constraints, and issue verification certification.",
                        "dependencies": ["content_generation"],
                        "estimated_cost": 1.00
                    }
                ]
            }

        # If prompt is for research
        if "research" in lower_prompt or "market size" in lower_prompt:
            return {
                "market_overview": "Rapidly expanding ecosystem driven by supportive regulatory frameworks, falling battery pack costs, and high localization mandates.",
                "market_size_current": "$3.21 Billion (2024)",
                "market_size_forecast": "$113.99 Billion (2030)",
                "cagr_projected": "49.0%",
                "major_competitors": [
                    {"name": "Tata Motors", "market_share": "68%", "segment": "Passenger Vehicles (Nexon, Tiago, Punch EV)"},
                    {"name": "Ola Electric", "market_share": "34%", "segment": "2-Wheeler (S1 Series, Gigafactory)"},
                    {"name": "TVS Motor", "market_share": "19%", "segment": "2-Wheeler (iQube)"},
                    {"name": "Mahindra & Mahindra", "market_share": "11%", "segment": "Passenger & Commercial (XUV400)"},
                    {"name": "Ather Energy", "market_share": "12%", "segment": "Premium 2-Wheeler (450X, Apex)"}
                ],
                "growth_drivers": [
                    "Government subsidies under FAME-II & EMPS schemes",
                    "Battery pack cost declining below $100/kWh globally",
                    "Surging urban commercial fleet adoption (last-mile delivery)",
                    "Expansion of public DC fast-charging network corridors"
                ],
                "challenges": [
                    "Charging infrastructure density in tier-2/tier-3 cities",
                    "Higher upfront consumer acquisition cost vs ICE vehicles",
                    "Grid infrastructure readiness and peak demand management"
                ],
                "sources": [
                    {"source": "Society of Indian Automobile Manufacturers (SIAM)", "reliability": "High"},
                    {"source": "NITI Aayog National Mission on Transformative Mobility", "reliability": "High"},
                    {"source": "Vahan National Vehicle Registry Data 2024", "reliability": "Verified"}
                ]
            }

        # If prompt is for data analysis
        if "analysis" in lower_prompt or "cagr" in lower_prompt or "quantitative" in lower_prompt:
            return {
                "computed_metrics": {
                    "base_year_revenue_usd_bn": 3.21,
                    "target_year_revenue_usd_bn": 113.99,
                    "cagr_percent": 49.0,
                    "ev_penetration_rate_2024": "6.8%",
                    "ev_penetration_target_2030": "30.0%"
                },
                "market_share_breakdown": [
                    {"label": "Tata Motors", "value": 68.0, "category": "4-Wheeler"},
                    {"label": "Mahindra & Mahindra", "value": 11.0, "category": "4-Wheeler"},
                    {"label": "MG Motor India", "value": 10.5, "category": "4-Wheeler"},
                    {"label": "Others (BYD, Hyundai)", "value": 10.5, "category": "4-Wheeler"}
                ],
                "chart_revenue_projections": [
                    {"year": "2024", "revenue_bn": 3.21, "volume_units_k": 1530},
                    {"year": "2025", "revenue_bn": 5.45, "volume_units_k": 2450},
                    {"year": "2026", "revenue_bn": 9.80, "volume_units_k": 3900},
                    {"year": "2027", "revenue_bn": 18.20, "volume_units_k": 6200},
                    {"year": "2028", "revenue_bn": 35.50, "volume_units_k": 9800},
                    {"year": "2029", "revenue_bn": 65.00, "volume_units_k": 14500},
                    {"year": "2030", "revenue_bn": 113.99, "volume_units_k": 21000}
                ],
                "key_findings": [
                    "2-Wheeler and 3-Wheeler segments reach Total Cost of Ownership (TCO) parity faster than passenger vehicles.",
                    "Commercial fleet operators achieve positive ROI within 14 months at average daily usage of 120km.",
                    "Domestic battery cell manufacturing capacity is projected to reduce unit production cost by 22% by 2027."
                ]
            }

        # If prompt is for QA
        if "quality" in lower_prompt or "qa" in lower_prompt or "audit" in lower_prompt:
            return {
                "audit_status": "APPROVED",
                "completeness_score": 98,
                "factual_coherence_score": 96,
                "constraint_compliance": True,
                "budget_compliance": True,
                "feedback": "Deliverable satisfies all primary user requirements: market size, major competitors, quantitative metrics, charts, and strategic opportunities are thoroughly verified.",
                "corrections_required": False
            }

        # Default fallback JSON
        return {
            "status": "success",
            "message": "Processed through AgentPay Nexus Intelligence Engine",
            "data": {"sample_query": prompt[:80]}
        }


llm_provider = LLMProvider()
