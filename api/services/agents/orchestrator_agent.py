from typing import Dict, Any, List
from sqlalchemy.orm import Session
from api.models.agent import AgentModel
from api.services.llm_provider import llm_provider


class OrchestratorAgent:
    """Master agent that analyzes objectives and crafts multi-agent execution plans."""

    AGENT_ID = "agent_orchestrator_00"

    async def create_plan(
        self,
        title: str,
        description: str,
        budget: float,
        currency: str = "USD",
        constraints: str = "",
        db: Session = None
    ) -> Dict[str, Any]:
        system_instruction = (
            "You are the Nexus Orchestrator, the central intelligence of an autonomous AI agent marketplace. "
            "Analyze the user's objective and budget to create a structured execution plan. "
            "Decompose the objective into distinct subtasks assigned to specialized marketplace agents: "
            "Research Agent (agent_research_01, $2.00), Data Analysis Agent (agent_analysis_02, $3.00), "
            "Content Agent (agent_content_03, $2.00), and Quality Assurance Agent (agent_qa_04, $1.00). "
            "Return valid JSON containing objective_summary, complexity_tier, estimated_total_cost, and subtasks list."
        )

        prompt = (
            f"Task Title: {title}\n"
            f"Detailed Description: {description}\n"
            f"Maximum Budget: ${budget:.2f} {currency}\n"
            f"Constraints: {constraints or 'Standard quality and accuracy'}\n\n"
            "Generate the structured multi-agent execution plan now."
        )

        has_creds = bool(llm_provider.gemini_key or llm_provider.openai_key)
        mode = "live_ai" if has_creds else "offline_scaffold"

        try:
            plan = await llm_provider.generate_json(prompt, system_instruction)
            plan["execution_mode"] = mode
        except Exception as e:
            plan = llm_provider._generate_fallback_json(f"plan Task Title: {title}", None)
            plan["execution_mode"] = mode
        
        # Ensure mandatory subtasks are present
        if "subtasks" not in plan or not plan["subtasks"]:
            plan = llm_provider._generate_fallback_json(f"plan Task Title: {title}", None)
            plan["execution_mode"] = mode

        # Reconcile estimated costs with DB if session is available
        if db:
            subtotal = 0.0
            for subtask in plan.get("subtasks", []):
                agent = db.query(AgentModel).filter(AgentModel.id == subtask.get("assigned_agent_id")).first()
                if agent:
                    subtask["estimated_cost"] = agent.price
                    subtask["agent_category"] = agent.category
                    subtotal += agent.price
            plan["estimated_total_cost"] = subtotal

        return plan
