from typing import Dict, Any, List
from sqlalchemy.orm import Session
from api.models.agent import AgentModel
from api.models.payment import InvoiceLineItem, PaymentSummary


class FinanceAgent:
    """Marketplace ledger agent. Computes transparent itemized invoices using trusted backend records."""

    AGENT_ID = "agent_finance_05"

    def calculate_invoice(
        self,
        task_id: str,
        task_title: str,
        budget: float,
        assigned_agent_ids: List[str],
        db: Session
    ) -> PaymentSummary:
        items: List[InvoiceLineItem] = []
        subtotal = 0.0

        # Query database directly - NEVER let LLM hallucinate or compute pricing
        for agent_id in assigned_agent_ids:
            agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
            if agent:
                unit_price = float(agent.price)
                subtotal += unit_price
                items.append(
                    InvoiceLineItem(
                        agent_id=agent.id,
                        agent_name=agent.name,
                        category=agent.category,
                        description=f"Specialized autonomous service execution for {agent.name}",
                        unit_price=unit_price,
                        quantity=1,
                        total=unit_price
                    )
                )

        subtotal = round(subtotal, 2)
        total_amount = subtotal  # zero platform surcharge for transparent ledger
        is_exceeded = total_amount > budget

        return PaymentSummary(
            task_id=task_id,
            task_title=task_title,
            subtotal=subtotal,
            platform_fee=0.0,
            total_amount=total_amount,
            currency="USD",
            items=items,
            is_budget_exceeded=is_exceeded,
            budget=budget
        )
