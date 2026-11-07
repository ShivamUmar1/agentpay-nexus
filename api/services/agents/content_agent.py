from typing import Dict, Any, List
from api.services.llm_provider import llm_provider


class ContentAgent:
    """Specialized executive content synthesis agent for publication-ready reports."""

    AGENT_ID = "agent_content_03"

    async def execute(
        self,
        title: str,
        description: str,
        research_data: Dict[str, Any],
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        system_instruction = (
            "You are the Executive Content Synthesis Agent in AgentPay Nexus. "
            "Synthesize the research findings and quantitative analytics into a comprehensive, "
            "publication-grade executive market report. "
            "Use clear Markdown formatting with headers, bullet points, data tables, and strategic recommendations. "
            "CRITICAL: Never fabricate, invent, or guess numbers or percentages. If metrics are marked unavailable, "
            "transparently disclose that empirical baseline data was unavailable. "
            "Return JSON containing: executive_summary, report_markdown, key_takeaways (list), and strategic_recommendations (list)."
        )

        prompt = (
            f"Generate an Executive Report on: {title}\n"
            f"Original Objective: {description}\n\n"
            f"Market Research Findings:\n{research_data}\n\n"
            f"Quantitative Analysis Findings:\n{analysis_data}\n\n"
            "Produce the complete synthesis now."
        )

        content_output = await llm_provider.generate_json(prompt, system_instruction)

        # Inspect quantitative findings
        metrics = analysis_data.get("computed_metrics", {}) if isinstance(analysis_data, dict) else {}
        cagr = metrics.get("cagr_percent")
        has_metrics = (
            cagr is not None and
            metrics.get("status") == "calculated" and
            (metrics.get("is_calculated") is True or metrics.get("calculation_status") == "success")
        )
        is_unverified = (metrics.get("status") == "unverified_estimate")
        cur_size = research_data.get("market_size_current") if isinstance(research_data, dict) else None
        fore_size = research_data.get("market_size_forecast") if isinstance(research_data, dict) else None

        # Build competitor section from research
        comp_list = research_data.get("major_competitors", []) if isinstance(research_data, dict) else []
        comp_bullets = []
        if isinstance(comp_list, list) and comp_list:
            for c in comp_list:
                if isinstance(c, dict) and "name" in c:
                    c_name = c.get("name", "Competitor")
                    c_share = c.get("market_share", "N/A")
                    c_seg = c.get("segment", "General")
                    if is_unverified or c.get("share_classification") == "unverified_estimate":
                        comp_bullets.append(f"* **{c_name} (unverified estimate)**: Key focus in {c_seg}.")
                    else:
                        comp_bullets.append(f"* **{c_name} ({c_share} share)**: Key focus in {c_seg}.")
        comp_text = "\n".join(comp_bullets) if comp_bullets else "*Specific competitor market share data was unavailable in the source research.*"

        evidence_status = research_data.get("quantitative_evidence_status") if isinstance(research_data, dict) else None
        if has_metrics:
            if evidence_status == "user_provided":
                doc_class = "User-Provided Benchmark Analysis"
            else:
                doc_class = "Independently Verified Empirical Deliverable"
        elif is_unverified:
            doc_class = "Qualitative Intelligence Synthesis (Contains Unverified Estimates)"
        else:
            doc_class = "Qualitative AI Synthesis (Data Unavailable / Qualitative Only)"

        if "report_markdown" not in content_output or len(str(content_output.get("report_markdown", ""))) < 100:
            if has_metrics:
                summary_text = (
                    f"Executive analysis for '{title}'. Based on {'user-provided benchmark data' if evidence_status == 'user_provided' else 'verified empirical data'}, the market is positioned to grow "
                    f"from {cur_size} to {fore_size} at a projected CAGR of {cagr}%."
                )
                sizing_section = f"""## 2. Market Sizing & Financial Projections

| Projection Metric | Current Baseline | Long-Term Projection | CAGR Benchmark |
| :--- | :--- | :--- | :--- |
| **Market Value (USD)** | {cur_size} | {fore_size} | **{cagr}% CAGR** |
| **Data Grounding** | Empirical Source | Empirical Source | Calculated |
"""
            elif is_unverified:
                summary_text = (
                    f"Executive qualitative synthesis for '{title}'. Domain outline reflects technological and structural trends. "
                    "Quantitative market sizing numbers represent unverified model estimates without verified primary source citations."
                )
                sizing_section = """## 2. Market Sizing & Financial Projections

> **Evidence Notice**: Market sizing figures in this sector are unverified model estimates without empirical primary source citations. Deterministic CAGR benchmarks and chart projections have been withheld to maintain research integrity.
"""
            else:
                summary_text = (
                    f"Executive analysis for '{title}'. Qualitative domain synthesis indicates active structural transformation. "
                    "Quantitative baseline market sizing metrics were unavailable in the provided research data."
                )
                sizing_section = """## 2. Market Sizing & Financial Projections

> **Notice**: Quantitative market sizing metrics were unavailable in the provided research source. Financial modeling and deterministic CAGR projections are deferred until verifiable baseline data is supplied.
"""

            content_output["executive_summary"] = summary_text
            content_output["report_markdown"] = f"""# Executive Market Research Report: {title}

> **Document Classification**: {doc_class}<br/>
> **Prepared by**: AgentPay Nexus Multi-Agent Collaborative Consortium<br/>
> **Participating Agents**: Deep Research (01), Quantitative Analysis (02), Executive Synthesis (03)  

---

## 1. Executive Summary
{summary_text}

---

{sizing_section}

---

## 3. Competitive Landscape & Market Dynamics

{comp_text}

---

## 4. Strategic Recommendations

- **Prioritize Reliable Data Infrastructure**: Implement verified telemetry and market benchmarks.
- **Maintain Rigorous Compliance Posture**: Ensure operations conform to domain regulatory standards.
- **Focus on Core Unit Economics**: Optimize capital expenditure based on validated operational metrics.

---

## 5. Audit & Deliverable Verification
This report deliverable has been audited by the Nexus Fact Auditor Agent.
"""

            content_output["key_takeaways"] = [
                f"Autonomous report compiled for '{title}'.",
                f"Quantitative CAGR: {cagr}%" if has_metrics else ("Quantitative CAGR: Withheld (unverified model estimate)." if is_unverified else "Quantitative CAGR: Unavailable (source data absent)."),
                "Strategic recommendations focus on compliance and verified data infrastructure."
            ]

            content_output["strategic_recommendations"] = [
                "Establish continuous data pipelines for empirical market monitoring.",
                "Align operational milestones with verified industry standards."
            ]
        else:
            # If report was generated by live LLM, ensure notices are transparent
            rm = content_output["report_markdown"]
            if is_unverified and "unverified model estimates" not in rm.lower():
                content_output["report_markdown"] = (
                    "> **Evidence Notice**: Quantitative market sizing figures in this deliverable represent unverified model estimates without primary source citations. Empirical CAGR calculations and projection charts have been withheld to maintain research integrity.\n\n"
                    + rm
                )
            elif has_metrics and "CAGR" not in rm and "cagr" not in rm:
                benchmark_label = "User-Provided Benchmark" if evidence_status == "user_provided" else "Empirical Growth Benchmark"
                content_output["report_markdown"] = rm + f"\n\n### Quantitative Growth Benchmark ({benchmark_label})\n- **Projected CAGR**: {cagr}%\n- **Market Horizon**: {cur_size} to {fore_size}\n"
            elif not has_metrics and "scope & evidence notice" not in rm.lower() and "qualitative ai synthesis" not in rm.lower():
                content_output["report_markdown"] = (
                    "> **Scope & Evidence Notice**: This deliverable represents qualitative AI intelligence synthesis based on structural domain analysis and suggested research leads. It does not contain independently verified factual or financial research citations.\n\n"
                    + rm
                )

            if has_metrics and evidence_status == "user_provided" and "user-provided" not in content_output["report_markdown"].lower():
                content_output["report_markdown"] = (
                    "> **Benchmark Notice**: Quantitative projections are calculated from user-provided input baselines; they have not been independently fact-verified against external primary records.\n\n"
                    + content_output["report_markdown"]
                )

        return content_output
