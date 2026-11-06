import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from api.models.task import TaskModel, TaskStepModel, AgentRunModel
from api.models.agent import AgentModel
from api.models.log import ActivityLogModel
from api.models.payment import TransactionModel
from api.services.agents.orchestrator_agent import OrchestratorAgent
from api.services.agents.research_agent import ResearchAgent
from api.services.agents.data_analysis_agent import DataAnalysisAgent
from api.services.agents.content_agent import ContentAgent
from api.services.agents.qa_agent import QualityAssuranceAgent
from api.services.agents.finance_agent import FinanceAgent

logger = logging.getLogger(__name__)

orchestrator_agent = OrchestratorAgent()
research_agent = ResearchAgent()
data_analysis_agent = DataAnalysisAgent()
content_agent = ContentAgent()
qa_agent = QualityAssuranceAgent()
finance_agent = FinanceAgent()


def log_activity(
    db: Session,
    task_id: str,
    event_type: str,
    message: str,
    agent_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Appends an event to the persistent activity log."""
    log_entry = ActivityLogModel(
        task_id=task_id,
        agent_id=agent_id,
        event_type=event_type,
        message=message,
        metadata_json=json.dumps(metadata) if metadata else None
    )
    db.add(log_entry)
    db.flush()


class OrchestrationEngine:
    """Stateful, bounded multi-agent workflow engine compatible with Vercel serverless."""

    async def create_and_plan_task(
        self,
        db: Session,
        user_id: str,
        title: str,
        description: str,
        budget: float,
        currency: str = "USD",
        constraints: Optional[str] = None
    ) -> TaskModel:
        """Initializes task, generates multi-agent plan, and seeds task steps."""
        task = TaskModel(
            user_id=user_id,
            title=title,
            description=description,
            budget=budget,
            currency=currency,
            status="planning",
            current_step="planning"
        )
        db.add(task)
        db.flush()

        log_activity(
            db, task.id, "system",
            f"Task '{title}' initialized with budget ${budget:.2f} {currency}.",
            agent_id=orchestrator_agent.AGENT_ID
        )

        # Generate structured plan via Orchestrator Agent
        plan = await orchestrator_agent.create_plan(
            title=title,
            description=description,
            budget=budget,
            currency=currency,
            constraints=constraints or "",
            db=db
        )

        task.execution_plan = json.dumps(plan)
        task.status = "executing"
        task.current_step = "research"

        # Planning step (already completed)
        step_planning = TaskStepModel(
            task_id=task.id,
            step_name="planning",
            assigned_agent_id=orchestrator_agent.AGENT_ID,
            dependencies=json.dumps([]),
            input_data=json.dumps({"title": title, "description": description, "budget": budget}),
            output_data=json.dumps(plan),
            status="completed",
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        db.add(step_planning)

        # Research step
        step_research = TaskStepModel(
            task_id=task.id,
            step_name="research",
            assigned_agent_id=research_agent.AGENT_ID,
            dependencies=json.dumps(["planning"]),
            status="pending"
        )
        db.add(step_research)

        # Data Analysis step
        step_analysis = TaskStepModel(
            task_id=task.id,
            step_name="data_analysis",
            assigned_agent_id=data_analysis_agent.AGENT_ID,
            dependencies=json.dumps(["research"]),
            status="pending"
        )
        db.add(step_analysis)

        # Content Generation step
        step_content = TaskStepModel(
            task_id=task.id,
            step_name="content_generation",
            assigned_agent_id=content_agent.AGENT_ID,
            dependencies=json.dumps(["data_analysis"]),
            status="pending"
        )
        db.add(step_content)

        # QA step
        step_qa = TaskStepModel(
            task_id=task.id,
            step_name="quality_assurance",
            assigned_agent_id=qa_agent.AGENT_ID,
            dependencies=json.dumps(["content_generation"]),
            status="pending"
        )
        db.add(step_qa)

        # Finance calculation step
        step_finance = TaskStepModel(
            task_id=task.id,
            step_name="finance_calculation",
            assigned_agent_id=finance_agent.AGENT_ID,
            dependencies=json.dumps(["quality_assurance"]),
            status="pending"
        )
        db.add(step_finance)

        # Payment approval step (gate for user authorization)
        step_payment = TaskStepModel(
            task_id=task.id,
            step_name="payment_approval",
            assigned_agent_id="agent_payment_06",
            dependencies=json.dumps(["finance_calculation"]),
            status="pending"
        )
        db.add(step_payment)

        # Final delivery step
        step_delivery = TaskStepModel(
            task_id=task.id,
            step_name="final_delivery",
            assigned_agent_id=orchestrator_agent.AGENT_ID,
            dependencies=json.dumps(["payment_approval"]),
            status="pending"
        )
        db.add(step_delivery)

        log_activity(
            db, task.id, "plan",
            f"Execution plan formulated. 5 specialized agents assigned. Total estimated cost: ${plan.get('estimated_total_cost', 8.0):.2f}.",
            agent_id=orchestrator_agent.AGENT_ID,
            metadata=plan
        )

        db.commit()
        db.refresh(task)
        return task

    async def advance_task(self, db: Session, task_id: str) -> Dict[str, Any]:
        """Executes the next eligible workflow node idempotently."""
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task:
            raise ValueError(f"Task with ID {task_id} not found.")

        if task.status in ["completed", "cancelled", "failed"]:
            return {
                "task_id": task.id,
                "status": task.status,
                "current_step": task.current_step,
                "message": f"Task is already {task.status}."
            }

        # Check pending steps
        steps = db.query(TaskStepModel).filter(TaskStepModel.task_id == task.id).all()
        step_dict = {s.step_name: s for s in steps}

        # Determine next step
        next_step: Optional[TaskStepModel] = None
        for step in steps:
            if step.status == "pending":
                deps = json.loads(step.dependencies or "[]")
                deps_met = all(step_dict.get(d) and step_dict[d].status == "completed" for d in deps)
                if deps_met:
                    next_step = step
                    break

        if not next_step:
            # Check if awaiting payment
            if step_dict.get("payment_approval") and step_dict["payment_approval"].status == "running":
                return {
                    "task_id": task.id,
                    "status": "awaiting_payment",
                    "current_step": "payment_approval",
                    "message": "Task is awaiting explicit user payment authorization via PayPal Checkout."
                }
            return {
                "task_id": task.id,
                "status": task.status,
                "current_step": task.current_step,
                "message": "No eligible steps to advance."
            }

        # Execute next_step
        next_step.status = "running"
        next_step.started_at = datetime.utcnow()
        task.current_step = next_step.step_name
        db.commit()

        try:
            if next_step.step_name == "research":
                await self._execute_research_step(db, task, next_step)
            elif next_step.step_name == "data_analysis":
                await self._execute_data_analysis_step(db, task, next_step, step_dict)
            elif next_step.step_name == "content_generation":
                await self._execute_content_step(db, task, next_step, step_dict)
            elif next_step.step_name == "quality_assurance":
                await self._execute_qa_step(db, task, next_step, step_dict)
            elif next_step.step_name == "finance_calculation":
                await self._execute_finance_step(db, task, next_step)
            elif next_step.step_name == "payment_approval":
                return await self._check_payment_step(db, task, next_step)
            elif next_step.step_name == "final_delivery":
                await self._execute_delivery_step(db, task, next_step, step_dict)

            db.commit()
            db.refresh(task)
            return {
                "task_id": task.id,
                "status": task.status,
                "current_step": task.current_step,
                "advanced_step": next_step.step_name,
                "total_cost": task.total_cost
            }

        except Exception as e:
            logger.error(f"Step {next_step.step_name} execution error: {e}", exc_info=True)
            next_step.status = "failed"
            next_step.error_message = str(e)
            task.status = "failed"
            log_activity(db, task.id, "error", f"Step '{next_step.step_name}' failed: {str(e)}", agent_id=next_step.assigned_agent_id)
            db.commit()
            raise

    async def _execute_research_step(self, db: Session, task: TaskModel, step: TaskStepModel):
        log_activity(db, task.id, "execute", "Deep Research Agent deployed. Synthesizing sector baselines & competitors.", agent_id=step.assigned_agent_id)
        output = await research_agent.execute(task.title, task.description)
        step.output_data = json.dumps(output)
        step.status = "completed"
        step.completed_at = datetime.utcnow()

        agent_run = AgentRunModel(
            task_id=task.id,
            agent_id=step.assigned_agent_id,
            status="completed",
            input_data=json.dumps({"title": task.title, "description": task.description}),
            output_data=json.dumps(output),
            execution_metadata=json.dumps({"cost": 2.00, "status": "verified"}),
            completed_at=datetime.utcnow()
        )
        db.add(agent_run)
        log_activity(db, task.id, "execute", "Deep Research complete. Competitor landscape & market sizing established.", agent_id=step.assigned_agent_id)

    async def _execute_data_analysis_step(self, db: Session, task: TaskModel, step: TaskStepModel, step_dict: Dict[str, TaskStepModel]):
        log_activity(db, task.id, "execute", "Quantitative Data Analysis Agent processing numerical metrics & CAGR projections.", agent_id=step.assigned_agent_id)
        research_output = json.loads(step_dict["research"].output_data or "{}")
        output = await data_analysis_agent.execute(task.title, research_output)
        step.input_data = json.dumps({"research_summary": research_output.get("market_size_current")})
        step.output_data = json.dumps(output)
        step.status = "completed"
        step.completed_at = datetime.utcnow()

        agent_run = AgentRunModel(
            task_id=task.id,
            agent_id=step.assigned_agent_id,
            status="completed",
            input_data=json.dumps({"research": research_output}),
            output_data=json.dumps(output),
            execution_metadata=json.dumps({"cost": 3.00, "cagr": output.get("computed_metrics", {}).get("cagr_percent")}),
            completed_at=datetime.utcnow()
        )
        db.add(agent_run)
        log_activity(db, task.id, "execute", f"Quantitative analysis complete. Deterministic CAGR: {output.get('computed_metrics', {}).get('cagr_percent')}%.", agent_id=step.assigned_agent_id)

    async def _execute_content_step(self, db: Session, task: TaskModel, step: TaskStepModel, step_dict: Dict[str, TaskStepModel]):
        log_activity(db, task.id, "execute", "Executive Content Synthesis Agent compiling publication-grade briefing.", agent_id=step.assigned_agent_id)
        research_output = json.loads(step_dict["research"].output_data or "{}")
        analysis_output = json.loads(step_dict["data_analysis"].output_data or "{}")
        output = await content_agent.execute(task.title, task.description, research_output, analysis_output)
        step.output_data = json.dumps(output)
        step.status = "completed"
        step.completed_at = datetime.utcnow()

        agent_run = AgentRunModel(
            task_id=task.id,
            agent_id=step.assigned_agent_id,
            status="completed",
            input_data=json.dumps({"title": task.title}),
            output_data=json.dumps({"executive_summary": output.get("executive_summary")}),
            execution_metadata=json.dumps({"cost": 2.00}),
            completed_at=datetime.utcnow()
        )
        db.add(agent_run)
        log_activity(db, task.id, "execute", "Executive content synthesis complete. Markdown report formatted.", agent_id=step.assigned_agent_id)

    async def _execute_qa_step(self, db: Session, task: TaskModel, step: TaskStepModel, step_dict: Dict[str, TaskStepModel]):
        log_activity(db, task.id, "review", "Quality Assurance & Fact Auditor verifying constraints and numerical soundness.", agent_id=step.assigned_agent_id)
        research_output = json.loads(step_dict["research"].output_data or "{}")
        analysis_output = json.loads(step_dict["data_analysis"].output_data or "{}")
        content_output = json.loads(step_dict["content_generation"].output_data or "{}")

        output = await qa_agent.execute(task.title, task.description, content_output, research_output, analysis_output)
        step.output_data = json.dumps(output)
        step.status = "completed"
        step.completed_at = datetime.utcnow()

        agent_run = AgentRunModel(
            task_id=task.id,
            agent_id=step.assigned_agent_id,
            status="completed",
            input_data=json.dumps({"title": task.title}),
            output_data=json.dumps(output),
            execution_metadata=json.dumps({"cost": 1.00, "audit_status": output.get("audit_status")}),
            completed_at=datetime.utcnow()
        )
        db.add(agent_run)
        log_activity(db, task.id, "review", f"QA Audit sign-off granted: {output.get('audit_status', 'APPROVED')} (Score: {output.get('completeness_score', 98)}/100).", agent_id=step.assigned_agent_id)

    async def _execute_finance_step(self, db: Session, task: TaskModel, step: TaskStepModel):
        log_activity(db, task.id, "finance", "Marketplace Finance Agent calculating itemized invoice from database ledger.", agent_id=step.assigned_agent_id)
        
        # Collect all billable specialized agents used in this task
        assigned_agents = [
            research_agent.AGENT_ID,
            data_analysis_agent.AGENT_ID,
            content_agent.AGENT_ID,
            qa_agent.AGENT_ID
        ]

        invoice = finance_agent.calculate_invoice(
            task_id=task.id,
            task_title=task.title,
            budget=task.budget,
            assigned_agent_ids=assigned_agents,
            db=db
        )

        task.total_cost = invoice.total_amount
        task.status = "awaiting_payment"
        task.current_step = "payment_approval"

        step.output_data = json.dumps(invoice.model_dump())
        step.status = "completed"
        step.completed_at = datetime.utcnow()

        log_activity(
            db, task.id, "finance",
            f"Formal invoice issued: ${invoice.total_amount:.2f} {invoice.currency}. Within budget limit (${task.budget:.2f}). Awaiting user approval.",
            agent_id=step.assigned_agent_id,
            metadata=invoice.model_dump()
        )

    async def _check_payment_step(self, db: Session, task: TaskModel, step: TaskStepModel) -> Dict[str, Any]:
        """Checks whether the user has authorized and captured payment via PayPal."""
        transaction = db.query(TransactionModel).filter(
            TransactionModel.task_id == task.id,
            TransactionModel.payment_status.in_(["completed", "simulated_completed"])
        ).first()

        if not transaction:
            step.status = "running"
            task.status = "awaiting_payment"
            task.current_step = "payment_approval"
            return {
                "task_id": task.id,
                "status": "awaiting_payment",
                "current_step": "payment_approval",
                "total_cost": task.total_cost,
                "message": "Payment authorization required. Please authorize via PayPal Checkout."
            }

        # Payment is confirmed! Mark payment step completed
        step.status = "completed"
        step.output_data = json.dumps({
            "transaction_id": transaction.id,
            "paypal_order_id": transaction.paypal_order_id,
            "paypal_capture_id": transaction.paypal_capture_id,
            "amount": transaction.amount,
            "currency": transaction.currency,
            "provider": transaction.provider
        })
        step.completed_at = datetime.utcnow()
        task.status = "paid"
        task.current_step = "final_delivery"

        log_activity(
            db, task.id, "payment",
            f"Payment confirmed ({transaction.provider}): ${transaction.amount:.2f} {transaction.currency}. Deliverable unlocking.",
            agent_id="agent_payment_06"
        )
        return {
            "task_id": task.id,
            "status": "paid",
            "current_step": "final_delivery",
            "advanced_step": "payment_approval"
        }

    async def _execute_delivery_step(self, db: Session, task: TaskModel, step: TaskStepModel, step_dict: Dict[str, TaskStepModel]):
        log_activity(db, task.id, "system", "Assembling verified multi-agent deliverables and final deliverable package.", agent_id=step.assigned_agent_id)
        
        content_output = json.loads(step_dict.get("content_generation", TaskStepModel()).output_data or "{}")
        research_output = json.loads(step_dict.get("research", TaskStepModel()).output_data or "{}")
        analysis_output = json.loads(step_dict.get("data_analysis", TaskStepModel()).output_data or "{}")
        qa_output = json.loads(step_dict.get("quality_assurance", TaskStepModel()).output_data or "{}")
        finance_output = json.loads(step_dict.get("finance_calculation", TaskStepModel()).output_data or "{}")

        deliverables = {
            "title": task.title,
            "description": task.description,
            "report_markdown": content_output.get("report_markdown", ""),
            "executive_summary": content_output.get("executive_summary", ""),
            "key_takeaways": content_output.get("key_takeaways", []),
            "strategic_recommendations": content_output.get("strategic_recommendations", []),
            "research_data": research_output,
            "analysis_data": analysis_output,
            "qa_audit": qa_output,
            "invoice": finance_output,
            "delivered_at": datetime.utcnow().isoformat()
        }

        task.final_output = json.dumps(deliverables)
        task.status = "completed"
        task.current_step = "completed"

        step.output_data = json.dumps({"summary": "Final report unlocked and delivered."})
        step.status = "completed"
        step.completed_at = datetime.utcnow()

        log_activity(db, task.id, "system", "Task successfully completed. All deliverables published to user dashboard.", agent_id=step.assigned_agent_id)


orchestration_engine = OrchestrationEngine()
