from typing import Dict, Any
from api.services.llm_provider import llm_provider


class ResearchAgent:
    """Specialized autonomous research agent for market intelligence and competitor discovery."""

    AGENT_ID = "agent_research_01"

    async def execute(self, title: str, description: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        system_instruction = (
            "You are the Deep Research Agent in the AgentPay Nexus marketplace. "
            "Conduct exhaustive industry and market research based on the user's objective. "
            "Never hallucinate fake URL sources or ungrounded statistics. "
            "Return structured JSON containing: market_overview, market_size_current, "
            "market_size_forecast, cagr_projected, major_competitors (array with name, market_share, segment), "
            "growth_drivers (array), challenges (array), and sources (array with source and reliability)."
        )

        prompt = (
            f"Conduct rigorous market research on:\n"
            f"Title: {title}\n"
            f"Details: {description}\n\n"
            "Format your findings into the requested structured JSON schema."
        )

        research_data = await llm_provider.generate_json(prompt, system_instruction)
        if "market_overview" not in research_data:
            research_data = llm_provider._generate_fallback_json("research " + title, None)

        return research_data
