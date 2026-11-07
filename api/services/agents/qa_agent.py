import re
from typing import Dict, Any, List, Optional, Tuple
from api.services.llm_provider import llm_provider


def detect_unsupported_quantitative_claims(text: str, allowed_benchmarks: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Detects quantitative market, business, and operational performance claims in narrative text:
    1. Market sizing & financial valuations (e.g. $140B market, valued at $230 billion)
    2. Sales & revenue forecasts (e.g. annual sales will reach $5 billion, revenue of $10B)
    3. Revenue / sales growth percentages (e.g. revenue will increase by 35%, sales will grow by 25%)
    4. Compound annual growth rates / CAGR (e.g. 13.2% CAGR, CAGR of 15%)
    5. Market share percentages (e.g. 60% market share, 35% share)
    6. Adoption & penetration rates (e.g. EV adoption will reach 40%, penetration of 25%)
    7. Shipment & physical volume targets (e.g. annual shipments will reach 2 million units, 500,000 units)
    8. Financial margin expansions (e.g. operating margin will improve by 8 percentage points, margin of 20%)
    9. Customer & subscriber counts (e.g. the sector will add 3 million customers, 10 million users)
    10. Operational uptime & SLA assertions (e.g. guarantees 99.9% uptime, achieved 99.99% availability)
    11. Latency, speed, & throughput performance assertions (e.g. latency improved by 40%, speed increased by 3x)
    12. Operational concurrency & load capacity assertions (e.g. supports 10,000 concurrent users)

    Excludes:
    - Calendar years (1900 to 2099)
    - Forecast horizons (e.g. '5-year', '10-year')
    - Hardware & physical specifications (e.g. 3nm, 2nm, 13.5nm, 0.55 NA, 500W, 300mm)
    - General list counts (e.g. 3 major players, 4 challenges)
    - Strict role-bound user benchmark numbers in their authorized context
    """
    if not text:
        return []

    # Parse role-bound benchmarks
    baseline_val = None
    forecast_val = None
    calc_cagr_val = None
    proj_cagr_val = None
    if allowed_benchmarks:
        if "baseline" in allowed_benchmarks and allowed_benchmarks["baseline"] is not None:
            try:
                baseline_val = round(float(allowed_benchmarks["baseline"]), 2)
            except (ValueError, TypeError):
                pass
        elif "current" in allowed_benchmarks and allowed_benchmarks["current"] is not None:
            try:
                baseline_val = round(float(allowed_benchmarks["current"]), 2)
            except (ValueError, TypeError):
                pass

        if "forecast" in allowed_benchmarks and allowed_benchmarks["forecast"] is not None:
            try:
                forecast_val = round(float(allowed_benchmarks["forecast"]), 2)
            except (ValueError, TypeError):
                pass

        if "calculated_cagr" in allowed_benchmarks and allowed_benchmarks["calculated_cagr"] is not None:
            try:
                calc_cagr_val = round(float(allowed_benchmarks["calculated_cagr"]), 2)
            except (ValueError, TypeError):
                pass
        elif "cagr" in allowed_benchmarks and allowed_benchmarks["cagr"] is not None:
            try:
                calc_cagr_val = round(float(allowed_benchmarks["cagr"]), 2)
            except (ValueError, TypeError):
                pass

        proj_cagr_val = None
        if "projected_cagr" in allowed_benchmarks and allowed_benchmarks["projected_cagr"] is not None:
            try:
                proj_cagr_val = round(float(allowed_benchmarks["projected_cagr"]), 2)
            except (ValueError, TypeError):
                pass

    findings: List[str] = []

    def has_company_preceding(idx: int) -> bool:
        start = max(0, idx - 45)
        window = text[start:idx]
        return bool(re.search(r'\b(?:tsmc|intel|samsung|apple|nvidia|amd|asml|qualcomm|company|firm|competitor|internal)\s+(?:will\s+)?(?:achieve|generate|reach|post|have|hit|report)?\s*(?:annual\s+)?(?:sales|revenue|budget)?\b', window, re.I))

    # 1. Market sizing & financial valuations / Sales forecasts
    sizing_patterns = [
        r'(?:annual\s+|total\s+|projected\s+)?(?:sales|revenue)\s+(?:(?:will|to|is\s+projected\s+to)\s+)?(?:reach|hit|exceed|be|total)\s+\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|million|m|trillion|t)\b',
        r'\$\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|b|million|m|trillion|t)\b',
        r'(\d+(?:\.\d+)?)\s*(?:billion|bn|trillion)\s*(?:usd|dollars)?\s*(?:market|industry|valuation|size|opportunity|foundry|segment|sector)',
        r'(?:valued\s+at|worth|reaching|reach|exceeding|surpassing|projected\s+to\s+reach)\s+\$?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|million|m|trillion)'
    ]

    for pat in sizing_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            val_str = m.group(1)
            full_match = m.group(0)
            try:
                val = round(float(val_str), 2)
                if 1900 <= val <= 2099:
                    continue

                start_idx = max(0, m.start() - 40)
                end_idx = min(len(text), m.end() + 40)
                local_window = text[start_idx:end_idx].lower()
                is_company = has_company_preceding(m.start())

                is_authorized_baseline = False
                if baseline_val is not None and abs(val - baseline_val) < 0.02 and not is_company:
                    if any(term in local_window for term in ["current", "baseline", "base year", "starting", "from $", "from", "valued at", "size of", "market of", "market was"]):
                        is_authorized_baseline = True

                is_authorized_forecast = False
                if forecast_val is not None and abs(val - forecast_val) < 0.02 and not is_company:
                    if any(term in local_window for term in ["forecast", "projected", "target", "to $", "reach $", "reach", "grow to", "reaching", "expand to"]):
                        is_authorized_forecast = True

                if is_authorized_baseline or is_authorized_forecast:
                    continue

                findings.append(f"Financial valuation / sales claim: '{full_match}'")
            except ValueError:
                pass

    # 2. Revenue growth / growth percentages
    growth_patterns = [
        r'(?:revenue|sales|earnings|income|profit)\s+(?:(?:will|to|is\s+projected\s+to|forecasted\s+to|expected\s+to)\s+)?(?:increase|grow|rise|reach|expand|surge)\s+(?:(?:by|to|at)\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent\b)',
        r'(?:revenue|sales)\s+growth\s*(?:of|is|at|[:=])?\s*(\d+(?:\.\d+)?)\s*(?:%|percent\b)',
        r'(?:increase|grow|growth|expansion)\s+(?:of|in)\s+(?:revenue|sales)\s+(?:(?:of|by)\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent\b)'
    ]
    for pat in growth_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            findings.append(f"Revenue growth claim: '{m.group(0)}'")

    # 3. CAGR / compound growth claims
    cagr_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:%|percent\b)\s*(?:cagr|compound\s+annual|growth\s+rate|annual\s+growth)',
        r'(?:cagr|compound\s+annual\s+growth\s+rate)(?:\s+of|\s+is|\s*[:=])?\s*(\d+(?:\.\d+)?)\s*(?:%|percent\b)'
    ]
    for pat in cagr_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            val_str = m.group(1)
            try:
                val = round(float(val_str), 2)
                if (calc_cagr_val is not None and abs(val - calc_cagr_val) < 0.6) or (proj_cagr_val is not None and abs(val - proj_cagr_val) < 0.1):
                    continue
                findings.append(f"CAGR growth claim: '{m.group(0)}'")
            except ValueError:
                pass

    # 4. Market share claims
    share_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:%|percent\b)\s*(?:market\s+share|share\s+of\s+the\s+market|global\s+share|industry\s+share)',
        r'(?:market\s+share|global\s+share|industry\s+share)(?:\s+of|\s+is|\s*[:=]|\s+at|\s+exceeding)?\s*(\d+(?:\.\d+)?)\s*(?:%|percent\b)'
    ]
    for pat in share_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            findings.append(f"Market share claim: '{m.group(0)}'")

    # 5. Adoption & penetration rate claims
    adoption_patterns = [
        r'(?:[a-z0-9_\-]+\s+)?(?:adoption|penetration)(?:\s+rate)?\s+(?:(?:will|is\s+projected\s+to|forecasted\s+to|expected\s+to|to)\s+)?(?:reach|hit|exceed|be|rise\s+to|grow\s+to)\s+(\d+(?:\.\d+)?)\s*(?:%|percent\b)',
        r'(\d+(?:\.\d+)?)\s*(?:%|percent\b)\s+(?:market\s+)?(?:adoption|penetration)\b'
    ]
    for pat in adoption_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            findings.append(f"Adoption rate claim: '{m.group(0)}'")

    # 6. Physical volume / shipment claims
    shipment_patterns = [
        r'(?:annual|quarterly|global|total)?\s*(?:shipments?|deliveries|units?|production|volume)\s+(?:(?:will|to|projected\s+to|expected\s+to)\s+)?(?:reach|hit|exceed|total|be)\s+(\d+(?:\.\d+)?)\s*(?:million|billion|k|m|b)?\s*(?:units?|vehicles?|devices?|wafers?)\b',
        r'(\d+(?:\.\d+)?)\s*(?:million|billion|k|m)\s*(?:units?|vehicles?|devices?)\s*(?:shipped|delivered|produced)\b'
    ]
    for pat in shipment_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            findings.append(f"Shipment volume claim: '{m.group(0)}'")

    # 7. Financial margin claims
    margin_patterns = [
        r'(?:operating|gross|net|profit)\s+margins?\s+(?:(?:will|to|is\s+expected\s+to)\s+)?(?:improve|increase|expand|grow|reach|be)\s+(?:(?:by|to|of)\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent\b|percentage\s+points?\b)',
        r'(\d+(?:\.\d+)?)\s*(?:%|percent\b|percentage\s+points?\b)\s+(?:operating|gross|net|profit)\s+margins?\b'
    ]
    for pat in margin_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            findings.append(f"Margin expansion claim: '{m.group(0)}'")

    # 8. Customer & subscriber counts
    customer_patterns = [
        r'(?:add|reach|gain|grow\s+to|attract)\s+(\d+(?:\.\d+)?)\s*(?:million|billion|k|m|b)\s*(?:customers?|users?|subscribers?|accounts?|clients?)\b',
        r'(\d+(?:\.\d+)?)\s*(?:million|billion|k|m)\s*(?:new\s+)?(?:customers?|users?|subscribers?)\b'
    ]
    for pat in customer_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            findings.append(f"Customer growth claim: '{m.group(0)}'")

    # 9. Uptime & SLA assertions
    uptime_patterns = [
        r'(?:guarantees?|achieved?|delivers?|maintains?|offers?|recorded|boasts?)\s+(\d+(?:\.\d+)?)\s*(?:%|percent\b)\s*(?:uptime|availability|sla|reliability)\b',
        r'(\d+(?:\.\d+)?)\s*(?:%|percent\b)\s*(?:uptime|availability|reliability)\s+(?:guarantee|sla|target|record|last\s+year|achieved|delivered)\b',
        r'(?:platform|service|system|infrastructure)\s+(?:guarantees?|achieved?|maintains?)\s+(\d+(?:\.\d+)?)\s*(?:%|percent\b)\s*(?:uptime|availability)\b'
    ]
    for pat in uptime_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            findings.append(f"Uptime/SLA claim: '{m.group(0)}'")

    # 10. Latency, speed multiplier & throughput claims
    latency_patterns = [
        r'(?:latency|response\s+time|ping|delay)\s+(?:(?:has\s+)?(?:improved|reduced|decreased|dropped|fell))\s+(?:(?:by|to|at)\s+)?(\d+(?:\.\d+)?)\s*(?:%|percent\b|ms\b|milliseconds\b)',
        r'(?:processing\s+speed|speed|throughput|execution\s+time)\s+(?:(?:has\s+)?(?:increased|improved|boosted|grew|accelerated))\s+(?:(?:by|at)\s+)?(\d+(?:\.\d+)?)\s*x\b',
        r'(\d+(?:\.\d+)?)\s*x\s+(?:faster|speedup|improvement\s+in\s+speed|higher\s+throughput)\b'
    ]
    for pat in latency_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            findings.append(f"Latency/speed claim: '{m.group(0)}'")

    # 11. Concurrency & capacity assertions
    concurrency_patterns = [
        r'(?:supports?|handles?|sustains?|processes?|serves?|scales?\s+to)\s+(\d+(?:,\d+)?(?:\.\d+)?)\s*(?:concurrent\s+users?|simultaneous\s+users?|active\s+users?|requests?\s+per\s+second|rps|tps|transactions?\s+per\s+second)\b',
        r'(\d+(?:,\d+)?(?:\.\d+)?)\s+(?:concurrent\s+users?|simultaneous\s+users?|active\s+users?|requests?\s+per\s+second|rps|tps)\s+(?:supported|handled|capacity)\b'
    ]
    for pat in concurrency_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            findings.append(f"Concurrency/capacity claim: '{m.group(0)}'")

    return findings


def extract_all_narrative_strings(obj: Any, visited: Optional[set] = None) -> List[str]:
    """Recursively extracts all free-text narrative strings across agent schemas."""
    if visited is None:
        visited = set()
    strings: List[str] = []

    ignored_keys = {
        "status", "agent_id", "assigned_agent_id", "execution_mode", "timestamp",
        "created_at", "completed_at", "status_code", "is_calculated", "calculation_status",
        "is_verified", "provenance", "quantitative_evidence_status", "share_classification",
        "source_classification", "model", "complexity_tier", "estimated_cost", "currency",
        "external_verification_performed", "is_payment_eligible",
        "market_size_current", "market_size_forecast", "cagr_projected", "user_benchmark_evidence",
        "market_size_current_provenance", "market_size_forecast_provenance", "chart_revenue_projections",
        "computed_metrics", "market_share", "market_share_breakdown"
    }

    if isinstance(obj, str):
        if len(obj.strip()) > 0:
            strings.append(obj)
    elif isinstance(obj, dict):
        obj_id = id(obj)
        if obj_id in visited:
            return strings
        visited.add(obj_id)
        for k, v in obj.items():
            if str(k).lower() in ignored_keys:
                continue
            strings.extend(extract_all_narrative_strings(v, visited))
    elif isinstance(obj, (list, tuple, set)):
        obj_id = id(obj)
        if obj_id in visited:
            return strings
        visited.add(obj_id)
        for item in obj:
            strings.extend(extract_all_narrative_strings(item, visited))
    return strings


def validate_market_share_breakdown(
    breakdown: Any,
    research_data: Optional[Dict[str, Any]] = None,
    task_prompt: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validates market_share_breakdown for provenance, empirical grounding, and mathematical consistency:
    1. Every percentage must be grounded in verified empirical evidence or explicit user prompt benchmarks.
    2. User-provided market size ($10B/$20B) does NOT authorize competitor market shares.
    3. Mathematical consistency: Shares must be positive, <= 100%, and total cannot exceed 100.5%.
    4. Unverified model estimates fail closed.
    """
    if not breakdown:
        return True, None

    if not isinstance(breakdown, list):
        return False, "Market share breakdown must be a structured list."

    if len(breakdown) == 0:
        return True, None

    # Check evidence status in research
    research_status = "unavailable"
    allowed_user_comps: Dict[str, float] = {}
    if isinstance(research_data, dict):
        research_status = research_data.get("quantitative_evidence_status", "unavailable")
        # Check if research explicitly recorded user-provided competitor share evidence
        user_evidence = research_data.get("user_benchmark_evidence", {})
        if isinstance(user_evidence, dict) and "competitor_shares" in user_evidence:
            allowed_user_comps = user_evidence["competitor_shares"]

    # If prompt text provided, also check if user explicitly stated competitor shares in prompt
    if task_prompt and not allowed_user_comps:
        # e.g. "Tata Motors 70% share", "Tata Motors has 70% market share"
        matches = re.findall(r'\b([A-Za-z0-9\s\-]+?)\s+(?:has|holds?|with|leads\s+with)?\s*(\d+(?:\.\d+)?)\s*%\s*(?:market\s+share|share)?\b', task_prompt, re.I)
        for comp_name, comp_share in matches:
            c_clean = comp_name.strip().lower()
            if not any(stop in c_clean for stop in ["market", "cagr", "revenue", "growth", "baseline", "target"]):
                try:
                    allowed_user_comps[c_clean] = float(comp_share)
                except ValueError:
                    pass

    total_share = 0.0
    for entry in breakdown:
        if not isinstance(entry, dict):
            return False, "Invalid market share entry structure."
        val = entry.get("value")
        label = str(entry.get("label", "")).strip().lower()
        if val is None:
            return False, f"Missing market share value for '{label}'."
        try:
            val_f = float(val)
        except (ValueError, TypeError):
            return False, f"Non-numeric market share value for '{label}'."

        if val_f <= 0 or val_f > 100:
            return False, f"Market share percentage {val_f}% for '{label}' is out of valid range (0-100%)."

        total_share += val_f

        # Provenance check: Did the user explicitly provide this competitor's share?
        is_user_authorized = False
        if research_status == "user_provided" and allowed_user_comps:
            for allowed_label, allowed_val in allowed_user_comps.items():
                if (allowed_label in label or label in allowed_label) and abs(val_f - allowed_val) < 1.0:
                    is_user_authorized = True
                    break

        if not is_user_authorized:
            return False, f"Unsupported model-generated market share for '{entry.get('label')}' ({val_f}%). Market share figures require explicit user-provided benchmarks or verified primary citations."

    # Consistency check: Total percentage cannot exceed 100.5%
    if total_share > 100.5:
        return False, f"Market share percentages sum to {total_share:.1f}%, exceeding 100%."

    return True, None


class QualityAssuranceAgent:
    """Specialized verification and fact auditing agent."""

    AGENT_ID = "agent_qa_04"

    async def execute(
        self,
        task_title: str,
        task_description: str,
        report_data: Dict[str, Any],
        research_data: Dict[str, Any],
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        # 1. Reject offline structural scaffolds from payment approval
        is_scaffold = (
            (isinstance(report_data, dict) and (report_data.get("execution_mode") == "offline_scaffold" or "_disclosure" in report_data)) or
            (isinstance(research_data, dict) and (research_data.get("execution_mode") == "offline_scaffold" or "_disclosure" in research_data)) or
            (isinstance(analysis_data, dict) and (analysis_data.get("execution_mode") == "offline_scaffold" or "_disclosure" in analysis_data))
        )
        if is_scaffold:
            return {
                "audit_status": "OFFLINE_SCAFFOLD",
                "completeness_score": 0,
                "factual_coherence_score": 0,
                "constraint_compliance": False,
                "budget_compliance": True,
                "feedback": "Deliverable generated in offline structural scaffold mode without live AI verification. Ineligible for payment authorization.",
                "corrections_required": True,
                "is_payment_eligible": False,
                "external_verification_performed": False,
                "deliverable_classification": "Offline Structural Scaffold"
            }

        # 2. Reject missing or incomplete deliverables
        report_text = report_data.get("report_markdown", "") if isinstance(report_data, dict) else ""
        if not report_text or len(report_text.strip()) < 50:
            return {
                "audit_status": "NEEDS_REVISION",
                "completeness_score": 15,
                "factual_coherence_score": 20,
                "constraint_compliance": False,
                "budget_compliance": False,
                "feedback": "Deliverable report markdown is missing or incomplete. Executive synthesis must be finalized before audit sign-off.",
                "corrections_required": True,
                "is_payment_eligible": False,
                "external_verification_performed": False,
                "deliverable_classification": "Incomplete Deliverable"
            }

        # 3. Reject unverified numerical claims from receiving verified factual-research approval
        research_status = research_data.get("quantitative_evidence_status") if isinstance(research_data, dict) else None
        analysis_metrics = analysis_data.get("computed_metrics", {}) if isinstance(analysis_data, dict) else {}
        is_unverified_estimates = (research_status == "unverified_estimate" or analysis_metrics.get("status") == "unverified_estimate")

        if is_unverified_estimates:
            return {
                "audit_status": "NEEDS_REVISION",
                "factual_verification_status": "UNVERIFIED_ESTIMATES",
                "completeness_score": 65,
                "factual_coherence_score": 50,
                "constraint_compliance": False,
                "budget_compliance": True,
                "feedback": "Deliverable contains unsupported numerical market sizing claims without empirical citations. Qualitative synthesis is noted, but factual quantitative research cannot receive verified approval.",
                "corrections_required": True,
                "is_payment_eligible": False,
                "external_verification_performed": False,
                "deliverable_classification": "Unverified Quantitative Estimates (Ineligible for Payment)"
            }

        if research_status == "verified_fact":
            # FAIL CLOSED: The backend does not possess an external web crawler or publisher verification engine.
            # Claims of verified_fact from LLMs or unverified sources are rejected early as unverified estimates.
            return {
                "audit_status": "NEEDS_REVISION",
                "factual_verification_status": "UNVERIFIED_ESTIMATES",
                "completeness_score": 60,
                "factual_coherence_score": 40,
                "constraint_compliance": False,
                "budget_compliance": True,
                "feedback": "Self-certified factual claims rejected: backend does not contain an independent primary-source verification engine.",
                "corrections_required": True,
                "is_payment_eligible": False,
                "external_verification_performed": False,
                "deliverable_classification": "Unverified Quantitative Estimates (Ineligible for Payment)",
                "verification_disclaimer": "Independent primary-source web retrieval verification is not configured; self-certified claims cannot be verified."
            }

        # 3b. Validate structured market share breakdown and competitors for provenance & mathematical consistency
        full_task_text = f"{task_title} {task_description}"

        if isinstance(research_data, dict):
            for c in research_data.get("major_competitors", []):
                if isinstance(c, dict) and c.get("market_share"):
                    if c.get("share_classification") == "unverified_estimate":
                        return {
                            "audit_status": "NEEDS_REVISION",
                            "factual_verification_status": "UNVERIFIED_ESTIMATES",
                            "completeness_score": 60,
                            "factual_coherence_score": 45,
                            "constraint_compliance": False,
                            "budget_compliance": True,
                            "feedback": f"Deliverable rejected: Competitor '{c.get('name')}' contains unverified market share ({c.get('market_share')}) without empirical citations.",
                            "corrections_required": True,
                            "is_payment_eligible": False,
                            "external_verification_performed": False,
                            "deliverable_classification": "Unverified Quantitative Estimates (Ineligible for Payment)"
                        }

        market_share_breakdown = analysis_data.get("market_share_breakdown") if isinstance(analysis_data, dict) else None
        if not market_share_breakdown and isinstance(report_data, dict):
            market_share_breakdown = report_data.get("market_share_breakdown")

        if market_share_breakdown:
            is_valid_share, share_err = validate_market_share_breakdown(market_share_breakdown, research_data, full_task_text)
            if not is_valid_share:
                return {
                    "audit_status": "NEEDS_REVISION",
                    "factual_verification_status": "UNVERIFIED_ESTIMATES",
                    "completeness_score": 60,
                    "factual_coherence_score": 45,
                    "constraint_compliance": False,
                    "budget_compliance": True,
                    "feedback": f"Deliverable rejected: {share_err}",
                    "corrections_required": True,
                    "is_payment_eligible": False,
                    "external_verification_performed": False,
                    "deliverable_classification": "Unverified Quantitative Estimates (Ineligible for Payment)"
                }

        # 4. Audit narrative fields to ensure unsupported quantitative claims cannot bypass structured gates
        narrative_parts = []
        if isinstance(research_data, dict):
            narrative_parts.extend(extract_all_narrative_strings(research_data))
        if isinstance(analysis_data, dict):
            narrative_parts.extend(extract_all_narrative_strings(analysis_data))
        if isinstance(report_data, dict):
            narrative_parts.extend(extract_all_narrative_strings(report_data))

        combined_narrative = "\n".join(narrative_parts)

        # Retrieve allowed benchmark numbers if user provided them
        allowed_benchmarks: Dict[str, Any] = {}
        if isinstance(research_data, dict) and research_status == "user_provided":
            size_cur = research_data.get("market_size_current")
            size_fore = research_data.get("market_size_forecast")
            if size_cur:
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(size_cur))
                if nums:
                    try:
                        allowed_benchmarks["baseline"] = float(nums[0])
                    except ValueError:
                        pass
            if size_fore:
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(size_fore))
                if nums:
                    try:
                        allowed_benchmarks["forecast"] = float(nums[0])
                    except ValueError:
                        pass
            cagr = analysis_metrics.get("cagr_percent")
            if cagr is not None and (analysis_metrics.get("status") == "calculated" or analysis_metrics.get("is_calculated") is True):
                try:
                    allowed_benchmarks["calculated_cagr"] = float(cagr)
                except (ValueError, TypeError):
                    pass

            cagr_proj = research_data.get("cagr_projected") or research_data.get("cagr_percent")
            if cagr_proj:
                c_nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(cagr_proj))
                if c_nums:
                    try:
                        allowed_benchmarks["projected_cagr"] = float(c_nums[0])
                    except ValueError:
                        pass

        narrative_claims = detect_unsupported_quantitative_claims(combined_narrative, allowed_benchmarks)
        if narrative_claims:
            return {
                "audit_status": "NEEDS_REVISION",
                "factual_verification_status": "UNVERIFIED_ESTIMATES",
                "completeness_score": 60,
                "factual_coherence_score": 45,
                "constraint_compliance": False,
                "budget_compliance": True,
                "feedback": f"Deliverable contains unsupported quantitative claims in narrative content without empirical citations: {'; '.join(narrative_claims[:3])}. Factual quantitative research cannot receive verified approval.",
                "corrections_required": True,
                "is_payment_eligible": False,
                "external_verification_performed": False,
                "deliverable_classification": "Unverified Quantitative Estimates (Ineligible for Payment)"
            }

        system_instruction = (
            "You are the Quality Assurance & Fact Auditor Agent in AgentPay Nexus. "
            "Audit the generated deliverables against the user's initial objective, constraints, and requirements. "
            "Verify numerical consistency, absence of unsupported factual assertions, and report completeness. "
            "Return JSON containing: audit_status ('APPROVED' or 'NEEDS_REVISION'), completeness_score (0-100), "
            "factual_coherence_score (0-100), constraint_compliance (boolean), budget_compliance (boolean), "
            "feedback (string), and corrections_required (boolean)."
        )

        prompt = (
            f"Audit the final deliverable for Task: {task_title}\n"
            f"Original Objective: {task_description}\n\n"
            f"Deliverable Content:\n{report_text[:5000]}\n\n"
            f"Research Context:\n{research_data}\n\n"
            f"Analysis Context:\n{analysis_data}\n\n"
            "Perform verification and return your official audit stamp in JSON."
        )

        qa_output = await llm_provider.generate_json(prompt, system_instruction)

        # Set payment eligibility flag
        qa_output["is_payment_eligible"] = (qa_output.get("audit_status") == "APPROVED")

        # Terminology & Evidence Scope Distinction:
        # Separate internal consistency/completeness from external independent factual verification.
        # System-controlled verification check: LLM self-certification is strictly rejected.
        has_calculated_metrics = (
            (analysis_metrics.get("is_calculated") is True or analysis_metrics.get("status") == "calculated") and
            analysis_metrics.get("cagr_percent") is not None
        )

        if research_status == "verified_fact":
            # FAIL CLOSED: The backend does not possess an external web crawler or publisher verification engine.
            # Claims of verified_fact from LLMs or unverified sources are rejected as unverified estimates.
            qa_output["audit_status"] = "NEEDS_REVISION"
            qa_output["factual_verification_status"] = "UNVERIFIED_ESTIMATES"
            qa_output["is_payment_eligible"] = False
            qa_output["external_verification_performed"] = False
            qa_output["deliverable_classification"] = "Unverified Quantitative Estimates (Ineligible for Payment)"
            qa_output["verification_disclaimer"] = "Independent primary-source web retrieval verification is not configured; self-certified claims cannot be verified."
            qa_output["feedback"] = "Self-certified factual claims rejected: backend does not contain an independent primary-source verification engine."
        elif has_calculated_metrics and research_status == "user_provided":
            qa_output["factual_verification_status"] = "USER_PROVIDED"
            qa_output["verification_scope"] = "USER_SUPPLIED_BENCHMARK"
            qa_output["external_verification_performed"] = False
            qa_output["deliverable_classification"] = "User-Provided Benchmark Analysis"
            qa_output["verification_disclaimer"] = (
                "Calculations derived deterministically from user-provided input parameters; "
                "not independently fact-verified by external primary records."
            )
        else:
            qa_output["factual_verification_status"] = "QUALITATIVE_SYNTHESIS"
            qa_output["verification_scope"] = "QUALITATIVE_AI_SYNTHESIS_WITH_SUGGESTED_LEADS"
            qa_output["external_verification_performed"] = False
            qa_output["deliverable_classification"] = "Qualitative AI Synthesis (Suggested Leads Only, Not Independently Verified)"
            qa_output["verification_disclaimer"] = (
                "Score reflects internal logical coherence and constraint compliance. "
                "Suggested research leads have not been independently fact-verified against external primary records."
            )

        return qa_output
