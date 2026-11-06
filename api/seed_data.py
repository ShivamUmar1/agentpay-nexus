import json
from sqlalchemy.orm import Session
from api.models.agent import AgentModel

INITIAL_AGENTS = [
    {
        "id": "agent_orchestrator_00",
        "name": "Nexus Orchestrator",
        "description": "Master coordination agent that analyzes high-level user objectives, crafts optimal multi-agent execution graphs, and manages end-to-end task lifecycles.",
        "category": "Orchestration",
        "capabilities": json.dumps([
            "Task Decomposition",
            "Multi-Agent Workflow Planning",
            "Dependency Resolution",
            "Dynamic Agent Discovery",
            "Quality Assurance Routing"
        ]),
        "supported_tasks": json.dumps([
            "market_research",
            "business_intelligence",
            "competitive_analysis",
            "technical_evaluation",
            "strategic_planning"
        ]),
        "pricing_model": "internal",
        "price": 0.0,
        "currency": "USD",
        "availability": "available",
        "rating": 5.0,
        "completed_tasks": 312,
        "icon": "Cpu",
        "estimated_time": "Instant"
    },
    {
        "id": "agent_research_01",
        "name": "Deep Research Agent",
        "description": "Autonomous market research specialist. Gathers authoritative domain data, industry statistics, market sizing, growth drivers, competitor footprints, and verifiable macro trends.",
        "category": "Research",
        "capabilities": json.dumps([
            "Industry Market Sizing",
            "Competitor Intelligence Gathering",
            "Regulatory & Macro Trend Analysis",
            "Target Demographic Mapping",
            "Primary & Secondary Source Synthesis"
        ]),
        "supported_tasks": json.dumps([
            "market_research",
            "competitor_scan",
            "trend_forecasting",
            "regulatory_review"
        ]),
        "pricing_model": "fixed_per_task",
        "price": 2.00,
        "currency": "USD",
        "availability": "available",
        "rating": 4.95,
        "completed_tasks": 248,
        "icon": "Search",
        "estimated_time": "30-45s"
    },
    {
        "id": "agent_analysis_02",
        "name": "Quantitative Data Analysis Agent",
        "description": "Deterministic quantitative analysis engine. Processes numerical inputs, computes CAGR, market shares, financial metrics, valuation multiples, and formats structured chart-ready datasets.",
        "category": "Analytics",
        "capabilities": json.dumps([
            "CAGR & Growth Projection Modeling",
            "Market Share Breakdown",
            "Deterministic Financial Computation",
            "Unit Economics & Margin Analysis",
            "Chart-Ready JSON Data Structuring"
        ]),
        "supported_tasks": json.dumps([
            "financial_modeling",
            "cagr_computation",
            "market_share_distribution",
            "risk_quantification"
        ]),
        "pricing_model": "fixed_per_task",
        "price": 3.00,
        "currency": "USD",
        "availability": "available",
        "rating": 4.98,
        "completed_tasks": 194,
        "icon": "BarChart3",
        "estimated_time": "20-30s"
    },
    {
        "id": "agent_content_03",
        "name": "Executive Content Synthesis Agent",
        "description": "Expert business report author. Transforms raw data and quantitative findings into polished, publication-grade executive briefings, strategic playbooks, and markdown dossiers.",
        "category": "Content",
        "capabilities": json.dumps([
            "Executive Summary Generation",
            "Structured Markdown Reporting",
            "Strategic Recommendation Synthesis",
            "Cross-Sectional Coherence",
            "Publication-Ready Formatting"
        ]),
        "supported_tasks": json.dumps([
            "executive_briefing",
            "research_report_synthesis",
            "strategic_dossier",
            "investor_memo"
        ]),
        "pricing_model": "fixed_per_task",
        "price": 2.00,
        "currency": "USD",
        "availability": "available",
        "rating": 4.92,
        "completed_tasks": 281,
        "icon": "FileText",
        "estimated_time": "25-35s"
    },
    {
        "id": "agent_qa_04",
        "name": "Quality Assurance & Fact Auditor",
        "description": "Rigorous verification agent. Audits deliverable completeness against original user constraints, detects inconsistencies, verifies logical soundings, and issues audit stamps.",
        "category": "Verification",
        "capabilities": json.dumps([
            "Constraint Compliance Verification",
            "Hallucination & Inconsistency Detection",
            "Completeness Scoring",
            "Single-Cycle Remediation Routing",
            "Deliverable Sign-Off Certification"
        ]),
        "supported_tasks": json.dumps([
            "deliverable_audit",
            "consistency_check",
            "factual_grounding_review",
            "compliance_verification"
        ]),
        "pricing_model": "fixed_per_task",
        "price": 1.00,
        "currency": "USD",
        "availability": "available",
        "rating": 4.97,
        "completed_tasks": 320,
        "icon": "CheckCircle2",
        "estimated_time": "15-20s"
    },
    {
        "id": "agent_finance_05",
        "name": "Marketplace Finance Agent",
        "description": "Trusted ledger & budget controller. Calculates itemized marketplace service costs from immutable database records, checks budget thresholds, and prepares formal invoices.",
        "category": "Financial Management",
        "capabilities": json.dumps([
            "Trusted Ledger Cost Aggregation",
            "Budget Limit Enforcement",
            "Itemized Line-Item Invoice Generation",
            "Currency Normalization",
            "Financial Audit Trail Logging"
        ]),
        "supported_tasks": json.dumps([
            "invoice_generation",
            "budget_compliance_check",
            "service_fee_calculation"
        ]),
        "pricing_model": "internal",
        "price": 0.0,
        "currency": "USD",
        "availability": "available",
        "rating": 5.0,
        "completed_tasks": 410,
        "icon": "DollarSign",
        "estimated_time": "Instant"
    },
    {
        "id": "agent_payment_06",
        "name": "PayPal Settlement Agent",
        "description": "Secure payment bridge agent. Interfaces with official PayPal Orders v2 APIs, verifies user authorization, creates and captures PayPal Sandbox orders, and confirms payment receipts.",
        "category": "Payment Management",
        "capabilities": json.dumps([
            "PayPal REST API v2 Handshake",
            "Server-Side Order Creation",
            "Capture Verification & Cryptographic Guard",
            "Idempotency Guarantee",
            "Receipt Emission & Deliverable Unlocking"
        ]),
        "supported_tasks": json.dumps([
            "paypal_order_creation",
            "paypal_capture_verification",
            "receipt_generation"
        ]),
        "pricing_model": "internal",
        "price": 0.0,
        "currency": "USD",
        "availability": "available",
        "rating": 5.0,
        "completed_tasks": 389,
        "icon": "CreditCard",
        "estimated_time": "Instant"
    },
    {
        "id": "agent_strategy_07",
        "name": "Strategic Forecasting Agent",
        "description": "Advanced macro modeling and scenario forecasting agent for long-range market outlooks, bull/base/bear projections, and regulatory disruption risk matrices.",
        "category": "Strategy",
        "capabilities": json.dumps([
            "Scenario Modeling (Bull/Base/Bear)",
            "Disruption Probability Matrix",
            "Regulatory Horizon Scanning",
            "M&A & Partner Synergies"
        ]),
        "supported_tasks": json.dumps([
            "strategic_forecasting",
            "scenario_planning",
            "risk_assessment"
        ]),
        "pricing_model": "fixed_per_task",
        "price": 2.50,
        "currency": "USD",
        "availability": "available",
        "rating": 4.88,
        "completed_tasks": 115,
        "icon": "Compass",
        "estimated_time": "30-40s"
    }
]


def seed_marketplace_agents(db: Session):
    """Inserts initial specialized marketplace agents if they don't already exist."""
    for agent_data in INITIAL_AGENTS:
        existing = db.query(AgentModel).filter(AgentModel.id == agent_data["id"]).first()
        if not existing:
            agent = AgentModel(**agent_data)
            db.add(agent)
        else:
            # Update fields if needed
            for k, v in agent_data.items():
                setattr(existing, k, v)
    db.commit()
