import re
from typing import Dict, Any, List, Optional
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
        units = round(current_val * 100)  # normalized volume units proxy
        trajectory.append({
            "year": str(year),
            "revenue_bn": round(current_val, 2),
            "volume_units_k": units
        })
        current_val *= (1.0 + rate)
    return trajectory


class DataAnalysisAgent:
    """Specialized quantitative data analysis agent with strict empirical grounding and deterministic calculation capabilities."""

    AGENT_ID = "agent_analysis_02"

    async def execute(self, title: str, research_data: Dict[str, Any]) -> Dict[str, Any]:
        system_instruction = (
            "You are the Quantitative Data Analysis Agent in AgentPay Nexus. "
            "Analyze the market research provided by the Research Agent. "
            "Extract verified numerical metrics, calculate key market benchmarks, determine market share distributions, "
            "and format chart-ready datasets. "
            "CRITICAL: Never fabricate, invent, or guess numbers or percentages. If numerical data is absent in the research, "
            "explicitly report it as unavailable. "
            "Return structured JSON with computed_metrics, market_share_breakdown, and key_findings."
        )

        prompt = (
            f"Analyze the research data for: {title}\n"
            f"Research Data: {research_data}\n\n"
            "Produce structured quantitative findings and chart-ready data points in JSON."
        )

        analysis_output = await llm_provider.generate_json(prompt, system_instruction)
        
        # Determine evidence status
        evidence_status = "unavailable"
        if isinstance(research_data, dict):
            evidence_status = research_data.get("quantitative_evidence_status")

        is_unverified = (evidence_status == "unverified_estimate")
        is_empirical_baseline = (evidence_status in ["verified_fact", "user_provided"] or evidence_status is None)

        # Ground quantitative baseline numbers strictly from research_data ONLY when empirical/verified
        start_val: Optional[float] = None
        end_val: Optional[float] = None
        years = 6
        
        if not is_unverified and is_empirical_baseline and isinstance(research_data, dict):
            size_cur = re.sub(r"\b(19\d\d|20\d\d)\b", " ", str(research_data.get("market_size_current", "")))
            size_fore = re.sub(r"\b(19\d\d|20\d\d)\b", " ", str(research_data.get("market_size_forecast", "")))
            cur_nums = re.findall(r"[-+]?\d*\.\d+|\d+", size_cur)
            fore_nums = re.findall(r"[-+]?\d*\.\d+|\d+", size_fore)
            if cur_nums:
                try:
                    v = float(cur_nums[0])
                    if v > 0:
                        start_val = v
                except ValueError:
                    pass
            if fore_nums:
                try:
                    v = float(fore_nums[0])
                    if v > 0:
                        end_val = v
                except ValueError:
                    pass

        # Ground calculations only when genuine positive verified values exist
        has_valid_metrics = (start_val is not None and end_val is not None and start_val > 0 and end_val > 0)

        if has_valid_metrics:
            cagr = calculate_cagr(start_val, end_val, years)
            chart_projections = generate_growth_trajectory(start_val, cagr, 2024, 7)
            computed_metrics = {
                "base_year_revenue_usd_bn": start_val,
                "target_year_revenue_usd_bn": end_val,
                "cagr_percent": cagr,
                "status": "calculated",
                "is_calculated": True,
                "calculation_status": "success",
                "provenance": "user_provided" if evidence_status == "user_provided" else "unverified_estimate",
                "is_verified": False  # Strictly False: deterministic calculation from user benchmarks is NOT external factual verification
            }
        elif is_unverified:
            cagr = None
            chart_projections = []  # Never construct charts from unverified estimates!
            computed_metrics = {
                "base_year_revenue_usd_bn": None,
                "target_year_revenue_usd_bn": None,
                "cagr_percent": None,
                "status": "unverified_estimate",
                "is_calculated": False,
                "calculation_status": "withheld",
                "provenance": "unverified_estimate",
                "message": "Market sizing figures represent unverified model estimates without verified empirical citations. Calculated CAGR and chart projections withheld to preserve data integrity.",
                "is_verified": False
            }
        else:
            cagr = None
            chart_projections = []  # Never fabricate charts when data is missing!
            computed_metrics = {
                "base_year_revenue_usd_bn": None,
                "target_year_revenue_usd_bn": None,
                "cagr_percent": None,
                "status": "unavailable",
                "is_calculated": False,
                "calculation_status": "unavailable",
                "provenance": "unavailable",
                "message": "Quantitative baseline metrics unavailable from research source. Projections deferred.",
                "is_verified": False
            }

        analysis_output["computed_metrics"] = computed_metrics
        analysis_output["chart_revenue_projections"] = chart_projections

        # Derive market shares strictly from research competitors if genuine numbers exist and are NOT unverified estimates
        comps = research_data.get("major_competitors", []) if isinstance(research_data, dict) else []
        shares = []
        if not is_unverified and isinstance(comps, list) and comps:
            for c in comps:
                if isinstance(c, dict) and "name" in c and "market_share" in c:
                    if c.get("share_classification") == "unverified_estimate":
                        continue
                    sh_str = str(c.get("market_share", ""))
                    sh_num = re.findall(r"\d+", sh_str)
                    if sh_num:
                        shares.append({
                            "label": c["name"],
                            "value": float(sh_num[0]),
                            "category": c.get("segment", "General")
                        })
        analysis_output["market_share_breakdown"] = shares  # Empty list if unverified or no competitors with verified shares exist

        if is_unverified:
            analysis_output["key_findings"] = [
                f"Quantitative market sizing for '{title}' represents unverified model estimates.",
                "Calculated CAGR and chart projections withheld pending verified empirical source citations."
            ]
        elif not has_valid_metrics:
            analysis_output["key_findings"] = [
                f"Quantitative baseline metrics for '{title}' unavailable in research data; analytical calculations deferred.",
                "Market projections require empirical source data before financial modeling can be conducted."
            ]
        elif "key_findings" not in analysis_output or not analysis_output["key_findings"]:
            analysis_output["key_findings"] = [
                f"Sustained compound annual growth rate (CAGR) of {cagr}% projects market expansion from ${start_val}B to ${end_val}B.",
                "Empirical research data provides verified baseline for long-term sector sizing."
            ]

        return analysis_output
