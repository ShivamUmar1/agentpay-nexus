import re
from typing import Dict, Any, List, Optional
from api.services.llm_provider import llm_provider


def extract_semantic_benchmarks(text: str) -> Dict[str, Any]:
    """
    Extracts explicitly role-bound market benchmark values from user prompt text:
    - baseline: Explicitly described baseline, current, or starting market size.
    - forecast: Explicitly described target, forecast, or projected market size.

    Rejects:
    - Unrelated financial figures (budgets, acquisitions, company revenue, R&D spend, costs).
    - Calendar years (1900 to 2099), forecast horizons (e.g. '5-year'), hardware specs (e.g. '2nm').
    - Ambiguous monetary figures without a clear market sizing role.
    """
    benchmarks: Dict[str, Any] = {"baseline": None, "forecast": None, "evidence": {}}
    if not text:
        return benchmarks

    # 1. Clean out explicitly non-market monetary phrases to avoid role hijacking
    # (e.g., 'acquisition target of $50 billion', 'budget of $10 billion', 'revenue was $20M')
    cleaned = text
    unrelated_patterns = [
        r'\b(?:acquisition|revenue|sales|profit|hiring|headcount|production|funding|r&d|spend|spending|internal|company)\s+target(?:\s+of)?\s*\$?\s*\d+(?:\.\d+)?\s*(?:billion|bn|b|million|m|trillion|t)?\b',
        r'\btarget(?:\s+of)?\s*\$?\s*\d+(?:\.\d+)?\s*(?:billion|bn|b|million|m|trillion|t)?\s+(?:revenue|sales|profit|arr|mrr|spend|spending|budget|headcount|income)\b',
        r'\b(?:budget|max(?:imum)?\s+budget|cost|fee|price)(?:\s+of|\s+is|\s*[:=])?\s*\$?\s*\d+(?:\.\d+)?\s*(?:billion|bn|b|million|m|trillion|t)?\b',
        r'\b(?:spend|spent|spending|revenue\s+was|r&d\s+of)(?:\s+of|\s+is|\s*[:=])?\s*\$?\s*\d+(?:\.\d+)?\s*(?:billion|bn|b|million|m|trillion|t)?\b'
    ]
    for upat in unrelated_patterns:
        cleaned = re.sub(upat, " [EXCLUDED_UNRELATED] ", cleaned, flags=re.IGNORECASE)

    # 2. Baseline / current market value patterns
    baseline_patterns = [
        r'(?:baseline|base|current|starting)\s+(?:market\s+)?(?:value|size|valuation)?\s*(?:of|is|was|at|:)?\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|b|million|m|trillion|t)?\b',
        r'from\s+\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|b|million|m|trillion|t)?\s*(?:baseline|base|current|starting)\b',
        r'(?:baseline|base|current|starting)\s*[:=]\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|b|million|m|trillion|t)?\b',
        r'\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|b|million|m|trillion|t)?\s*(?:baseline|base\s+year)\b',
        r'baseline\s+\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|b|million|m|trillion|t)?\b'
    ]

    # 3. Target / forecast market value patterns
    forecast_patterns = [
        r'(?:target|forecast|projected|future)\s+(?:market\s+)?(?:value|size|valuation)?\s*(?:of|is|was|at|to|reach|:)?\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|b|million|m|trillion|t)?\b',
        r'to\s+\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|b|million|m|trillion|t)?\s*(?:target|forecast|projected|projection)\b',
        r'(?:target|forecast|projected|future)\s*[:=]\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|b|million|m|trillion|t)?\b',
        r'\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|b|million|m|trillion|t)?\s*(?:target|forecast)\b',
        r'target\s+\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|b|million|m|trillion|t)?\b'
    ]

    for pat in baseline_patterns:
        m = re.search(pat, cleaned, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if not (1900 <= val <= 2099):
                benchmarks["baseline"] = val
                benchmarks["evidence"]["baseline"] = m.group(0).strip()
                break

    for pat in forecast_patterns:
        m = re.search(pat, cleaned, re.IGNORECASE)
        if m:
            val = float(m.group(1))
            if not (1900 <= val <= 2099):
                if benchmarks["evidence"].get("baseline") != m.group(0).strip():
                    benchmarks["forecast"] = val
                    benchmarks["evidence"]["forecast"] = m.group(0).strip()
                    break

    # 4. Extract explicit competitor market shares if provided by user in prompt
    # (e.g. "Tata Motors 70% share", "Tata Motors has 70% market share")
    comp_matches = re.findall(r'\b([A-Za-z0-9\s\-]+?)\s+(?:has|holds?|with|leads\s+with)?\s*(\d+(?:\.\d+)?)\s*%\s*(?:market\s+share|share)?\b', text, re.I)
    comp_shares = {}
    for comp_name, comp_share in comp_matches:
        c_clean = comp_name.strip().lower()
        if not any(stop in c_clean for stop in ["market", "cagr", "revenue", "growth", "baseline", "target", "forecast", "size"]):
            try:
                comp_shares[c_clean] = float(comp_share)
            except ValueError:
                pass
    if comp_shares:
        benchmarks["evidence"]["competitor_shares"] = comp_shares

    return benchmarks


def extract_numeric_value(val_str: Any) -> Optional[float]:
    """Extracts the first positive numeric magnitude from a string, ignoring calendar years."""
    if not val_str:
        return None
    cleaned = re.sub(r"\b(19\d\d|20\d\d)\b", " ", str(val_str))
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", cleaned)
    if nums:
        try:
            v = float(nums[0])
            if v > 0:
                return v
        except ValueError:
            pass
    return None


class ResearchAgent:
    """Specialized autonomous research agent for market intelligence and competitor discovery."""

    AGENT_ID = "agent_research_01"

    async def execute(self, title: str, description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        system_instruction = (
            "You are the Deep Research Agent in the AgentPay Nexus marketplace. "
            "Conduct exhaustive industry and market research based on the user's objective. "
            "Never hallucinate fake URL sources or ungrounded statistics. "
            "QUANTITATIVE EVIDENCE INTEGRITY RULES: "
            "For all quantitative claims, you MUST distinguish between: "
            "1) 'verified_fact' (supported by specific, verifiable primary empirical citations), "
            "2) 'user_provided' (explicitly stated in the user's prompt or title), "
            "3) 'unverified_estimate' (model-generated projections without specific evidence citations), and "
            "4) 'unavailable' (data absent). "
            "When specific verified publication citations are unavailable, you MUST classify numerical market sizes, "
            "growth rates, and market shares as 'unverified_estimate' or null. "
            "Organizations or publications without specific URL/page evidence MUST be classified as suggested research leads ('suggested_lead'), never verified citations. "
            "Return structured JSON containing: "
            "market_overview (string), "
            "quantitative_evidence_status ('verified_fact' | 'user_provided' | 'unverified_estimate' | 'unavailable'), "
            "market_size_current (string or null), "
            "market_size_forecast (string or null), "
            "cagr_projected (string or null), "
            "major_competitors (array of objects with name, market_share, segment, share_classification: 'verified' | 'unverified_estimate' | 'unavailable'), "
            "growth_drivers (array of strings), "
            "challenges (array of strings), and "
            "sources (array of objects with source: string, source_classification: 'suggested_lead', notes: string)."
        )

        prompt = (
            f"Conduct rigorous market research on:\n"
            f"Title: {title}\n"
            f"Details: {description}\n\n"
            "Format your findings into the requested structured JSON schema."
        )

        research_data = await llm_provider.generate_json(prompt, system_instruction)

        # Enforce quantitative evidence classification integrity - Prevent LLM Self-Certification
        if isinstance(research_data, dict):
            # 1. Sanitize all model sources: Gemini cannot self-certify sources as verified citations
            for s in research_data.get("sources", []):
                if isinstance(s, dict):
                    s["source_classification"] = "suggested_lead"

            # 2. Extract numeric values from research output
            cur_val = extract_numeric_value(research_data.get("market_size_current"))
            fore_val = extract_numeric_value(research_data.get("market_size_forecast"))
            has_nums = bool(cur_val is not None or fore_val is not None or research_data.get("cagr_projected"))

            # 3. Extract role-bound user benchmark values from prompt
            benchmarks = extract_semantic_benchmarks(title + " " + description)
            research_data["user_benchmark_evidence"] = benchmarks.get("evidence", {})

            # 4. Sanitize major_competitors: model cannot self-certify competitor market shares
            allowed_comp_shares = benchmarks.get("evidence", {}).get("competitor_shares", {})
            for c in research_data.get("major_competitors", []):
                if isinstance(c, dict):
                    c_name = str(c.get("name", "")).strip().lower()
                    c_share = extract_numeric_value(c.get("market_share"))
                    is_user_comp = False
                    if c_share is not None and allowed_comp_shares:
                        for u_name, u_val in allowed_comp_shares.items():
                            if (u_name in c_name or c_name in u_name) and abs(c_share - u_val) < 1.0:
                                is_user_comp = True
                                break
                    c["share_classification"] = "user_provided" if is_user_comp else "unverified_estimate"

            cur_is_user = (
                benchmarks["baseline"] is not None and
                cur_val is not None and
                abs(cur_val - benchmarks["baseline"]) < 0.01
            )
            fore_is_user = (
                benchmarks["forecast"] is not None and
                fore_val is not None and
                abs(fore_val - benchmarks["forecast"]) < 0.01
            )

            research_data["market_size_current_provenance"] = "user_provided" if cur_is_user else ("unverified_estimate" if cur_val is not None else "unavailable")
            research_data["market_size_forecast_provenance"] = "user_provided" if fore_is_user else ("unverified_estimate" if fore_val is not None else "unavailable")

            if not has_nums:
                research_data["quantitative_evidence_status"] = "unavailable"
            elif cur_is_user and fore_is_user:
                research_data["quantitative_evidence_status"] = "user_provided"
            else:
                # FAIL CLOSED: Any model-generated numbers not explicitly provided in the prompt are unverified estimates.
                # Gemini cannot self-certify as verified_fact without independent primary-source verification.
                research_data["quantitative_evidence_status"] = "unverified_estimate"

        return research_data
