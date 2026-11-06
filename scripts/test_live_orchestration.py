import asyncio
import sys
import json

sys.path.insert(0, ".")
from api.database import get_db_context
from api.services.orchestrator import orchestration_engine

async def main():
    print("=== TESTING ORCHESTRATOR & SPECIALIZED AGENTS WITH LIVE GEMINI ===")
    with get_db_context() as db:
        task = await orchestration_engine.create_and_plan_task(
            db=db,
            user_id="user_test_gemini",
            title="Autonomous EV Battery Supply Chain Audit",
            description="Analyze key lithium battery cathode suppliers, supply risks, and import dependency for Indian EV manufacturers.",
            budget=8.00,
            currency="USD"
        )
        print("✓ Task Created & Planned Successfully:")
        print(f"  Task ID: {task.id}")
        print(f"  Status: {task.status}")
        print(f"  Current Step: {task.current_step}")
        plan = json.loads(task.execution_plan) if task.execution_plan else {}
        print(f"  Objective Summary: {plan.get('objective_summary')}")
        print(f"  Complexity: {plan.get('complexity_tier')}")
        print(f"  Estimated Cost: ${plan.get('estimated_total_cost')}")
        print(f"  Subtasks Count: {len(plan.get('subtasks', []))}")
        for st in plan.get('subtasks', []):
            print(f"   * {st.get('step_name')} -> {st.get('assigned_agent_id')} (${st.get('estimated_cost')})")

        # Now advance step 1: research agent
        print("\n=== ADVANCING STEP: RESEARCH AGENT ===")
        adv_res = await orchestration_engine.advance_task(db=db, task_id=task.id)
        print(f"  Status after advance: {adv_res.get('status')}")
        print(f"  Current Step: {adv_res.get('current_step')}")
        print(f"  Advanced Step: {adv_res.get('advanced_step')}")

        print("\nORCHESTRATOR & AGENT REASONING TEST COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())

