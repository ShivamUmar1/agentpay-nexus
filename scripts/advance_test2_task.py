import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath("."))

from api.database import get_active_session
from api.models import TaskModel, TaskStepModel, TransactionModel
from api.services.orchestrator import orchestration_engine, log_activity
from api.services.paypal_service import paypal_service
from api.services.agents.finance_agent import FinanceAgent

finance_agent = FinanceAgent()

TASK_ID = "e2a619e7-7d06-4061-bce0-9ec7e5dbb629"

async def advance_pipeline():
    print(f"=== ADVANCING TEST 2 TASK {TASK_ID} VIA ORCHESTRATION ENGINE ===\n")
    
    with get_active_session() as db:
        task = db.query(TaskModel).filter(TaskModel.id == TASK_ID).first()
        if not task:
            print("Task not found!")
            return
            
        print("Initial Status:", task.status)
        
        step_num = 1
        while task.status not in ["awaiting_payment", "completed", "failed"] and step_num <= 10:
            print(f"\n[Cycle {step_num}] Advancing step...")
            result = await orchestration_engine.advance_task(db=db, task_id=TASK_ID)
            print("  Result message:", result.get("message"))
            print("  Completed step:", result.get("completed_step"))
            print("  Next step:", result.get("next_step"))
            
            db.refresh(task)
            print(f"  Current DB Status: {task.status}")
            if task.status == "awaiting_payment":
                print("\n=> Successfully reached awaiting_payment status!")
                break
            step_num += 1
            await asyncio.sleep(1)

        # Calculate trusted backend invoice
        assigned_agents = ["agent_research_01", "agent_analysis_02", "agent_content_03", "agent_qa_04"]
        invoice = finance_agent.calculate_invoice(
            task_id=task.id,
            task_title=task.title,
            budget=task.budget,
            assigned_agent_ids=assigned_agents,
            db=db
        )
        task.total_cost = invoice.total_amount
        db.commit()

        print("\n=== TRUSTED BACKEND INVOICE CALCULATION ===")
        print("Task Title:", invoice.task_title)
        print("Subtotal:", invoice.subtotal)
        print("Platform Fee:", invoice.platform_fee)
        print(f"Total Amount: ${invoice.total_amount:.2f} {invoice.currency}")
        print("Line items count:", len(invoice.items))
        for item in invoice.items:
            print(f"  - {item.agent_name} ({item.category}): ${item.total:.2f} USD")
            
        # Create fresh PayPal Orders v2 Order
        print("\n=== CREATING FRESH PAYPAL ORDERS V2 ORDER ===")
        return_url = f"https://agentpay-nexus.vercel.app/tasks/{TASK_ID}?approved=true"
        cancel_url = f"https://agentpay-nexus.vercel.app/tasks/{TASK_ID}?cancelled=true"
        
        order_res = await paypal_service.create_order(
            task_id=task.id,
            task_title=task.title,
            amount=invoice.total_amount,
            currency="USD",
            items=invoice.items,
            return_url=return_url,
            cancel_url=cancel_url
        )
        
        print("Order Created!")
        print("Order ID:", order_res.get("order_id"))
        print("Status:", order_res.get("status"))
        print("Provider:", order_res.get("provider"))
        print("Approval URL:", order_res.get("approval_url"))

        # Persist transaction in Supabase PostgreSQL
        existing_tx = db.query(TransactionModel).filter(
            TransactionModel.task_id == task.id,
            TransactionModel.payment_status == "pending"
        ).first()

        if existing_tx:
            existing_tx.paypal_order_id = order_res["order_id"]
            existing_tx.amount = invoice.total_amount
            existing_tx.provider = order_res["provider"]
        else:
            new_tx = TransactionModel(
                user_id="user_guest_01",
                task_id=task.id,
                paypal_order_id=order_res["order_id"],
                amount=invoice.total_amount,
                currency="USD",
                payment_status="pending",
                provider=order_res["provider"]
            )
            db.add(new_tx)

        log_activity(
            db, task.id, "payment",
            f"Fresh PayPal order created for Test 2: {order_res['order_id']} for ${invoice.total_amount:.2f} USD.",
            agent_id="agent_payment_06"
        )
        db.commit()
        print("Transaction record persisted in Supabase PostgreSQL!")
        
        # Verify order details on PayPal
        details = await paypal_service.get_order(order_res["order_id"])
        pu = details.get("purchase_units", [{}])[0]
        print("\nPayPal Verified Amount:", pu.get("amount"))
        print("PayPal Verified Payee:", pu.get("payee"))

if __name__ == "__main__":
    asyncio.run(advance_pipeline())
