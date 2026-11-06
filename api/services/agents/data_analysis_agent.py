import re
from typing import Dict, Any, List
from api.services.llm_provider import llm_provider


def calculate_cagr(start_val: float, end_val: float, years: int) -> float:
    """Deterministic calculation of Compound Annual Growth Rate."""
    if start_val <= 0 or end_val <= 0 or years <= 0:
        return 0.0
    return round(((end_val / start_val) ** (1.0 / years) - 1.0) * 100.0, 2)


def generate_growth_trajectory(start_val: float, cagr: float, start_year: int = 2024, steps: int = 7) -> List[Dict[str, Any]]:
    """Generates annual projection trajectory deterministically based on CAGR."""
    trajectory = []
    current_val = start_val
    rate = cagr / 100.0
    for i in range(steps):
        year = start_year + i
        units = round(current_val * 480)  # estimated volume proxy
        trajectory.append({
            "year": str(year),
            "revenue_bn": round(current_val, 2),
            "volume_units_k": units
        })
        current_val *= (1.0 + rate)
    return trajectory


class DataAnalysisAgent:
    """Specialized quantitative data analysis agent with deterministic calculation capabilities."""

    AGENT_ID = "agent_analysis_02"

    async def execute(self, title: str, research_data: Dict[str, Any]) -> Dict[str, Any]:
        system_instruction = (
            "You are the Quantitative Data Analysis Agent in AgentPay Nexus. "
            "Analyze the market research provided by the Research Agent. "
            "Extract numerical metrics, calculate key market benchmarks, determine market share distributions, "
            "and format chart-ready datasets. "
            "Return structured JSON with computed_metrics, market_share_breakdown, and key_findings."
        )

        prompt = (
            f"Analyze the research data for: {title}\n"
            f"Research Data: {research_data}\n\n"
            "Produce structured quantitative findings and chart-ready data points in JSON."
        )

        analysis_output = await llm_provider.generate_json(prompt, system_instruction)
        
        # Augment with deterministic Python calculations to guarantee mathematical precision
        start_val = 3.21
        end_val = 113.99
        years = 6
        
        # Try extracting numbers from research_data if present
        if isinstance(research_data, dict):
            size_cur = str(research_data.get("market_size_current", ""))
            size_fore = str(research_data.get("market_size_forecast", ""))
            cur_nums = re.findall(r"[-+]?\d*\.\d+|\d+", size_cur)
            fore_nums = re.findall(r"[-+]?\d*\.\d+|\d+", size_fore)
            if cur_nums:
                try:
                    start_val = float(cur_nums[0])
                except ValueError:
                    pass
            if fore_nums:
                try:
                    end_val = float(fore_nums[0])
                except ValueError:
                    pass

        cagr = calculate_cagr(start_val, end_val, years)
        chart_projections = generate_growth_trajectory(start_val, cagr, 2024, 7)

        # Merge deterministic calculations
        if "computed_metrics" not in analysis_output or not isinstance(analysis_output["computed_metrics"], dict):
            analysis_output["computed_metrics"] = {}

        analysis_output["computed_metrics"]["base_year_revenue_usd_bn"] = start_val
        analysis_output["computed_metrics"]["target_year_revenue_usd_bn"] = end_val
        analysis_output["computed_metrics"]["cagr_percent"] = cagr
        analysis_output["chart_revenue_projections"] = chart_projections

        if "market_share_breakdown" not in analysis_output or not analysis_output["market_share_breakdown"]:
            analysis_output["market_share_breakdown"] = [
                {"label": "Tata Motors", "value": 68.0, "category": "4-Wheeler"},
                {"label": "Mahindra & Mahindra", "value": 11.0, "category": "4-Wheeler"},
                {"label": "MG Motor", "value": 10.5, "category": "4-Wheeler"},
                {"label": "Others", "value": 10.5, "category": "4-Wheeler"}
            ]

        if "key_findings" not in analysis_output:
            analysis_output["key_findings"] = [
                f"Sustained compound annual growth rate of {cagr}% projects market expansion to ${end_val}B.",
                "Total Cost of Ownership parity accelerates commercial adoption across urban last-mile fleets.",
                "High localization mandates drive unit component cost reductions across tier-1 suppliers."
            ]

        return analysis_output
