import asyncio
import json
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import httpx
from api.config import settings
from api.services.paypal_service import paypal_service
from api.database import get_active_session
from api.models import TaskModel, TransactionModel, TaskStepModel

async def verify_test2():
    print("=== INDEPENDENT VERIFICATION OF TEST 2 ===\n")
    
    order_id = "3NU881071F2178519"
    capture_id = "4XF639955L031754T"
    
    token = await paypal_service.get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Get Order from PayPal
        order_res = await client.get(
            f"{settings.paypal_endpoint}/v2/checkout/orders/{order_id}",
            headers=headers
        )
        print("PayPal Order API Status Code:", order_res.status_code)
        order_data = order_res.json()
        print("Order ID:", order_data.get("id"))
        print("Order Status:", order_data.get("status"))
        print("Order Intent:", order_data.get("intent"))
        
        pu = order_data.get("purchase_units", [{}])[0]
        print("Order Amount:", pu.get("amount"))
        print("Payee:", pu.get("payee"))
        
        payments = pu.get("payments", {})
        captures = payments.get("captures", [])
        print("Captures found in order:", len(captures))
        for c in captures:
            print("  Capture ID:", c.get("id"))
            print("  Capture Status:", c.get("status"))
            print("  Capture Amount:", c.get("amount"))
            
        # 2. Get Capture Details from PayPal
        cap_res = await client.get(
            f"{settings.paypal_endpoint}/v2/payments/captures/{capture_id}",
            headers=headers
        )
        print("\nPayPal Capture API Status Code:", cap_res.status_code)
        cap_data = cap_res.json()
        print("Capture ID:", cap_data.get("id"))
        print("Capture Status:", cap_data.get("status"))
        print("Capture Amount:", cap_data.get("amount"))
        print("Final Capture:", cap_data.get("final_capture"))
        print("Seller Protection:", cap_data.get("seller_protection"))
        print("Seller Receivable Breakdown:", cap_data.get("seller_receivable_breakdown"))
        print("Create Time:", cap_data.get("create_time"))
        print("Update Time:", cap_data.get("update_time"))

    # 3. Supabase DB Verification
    print("\n=== SUPABASE POSTGRESQL VERIFICATION ===")
    task_id = "e2a619e7-7d06-4061-bce0-9ec7e5dbb629"
    with get_active_session() as db:
        task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if task:
            print("Task ID:", task.id)
            print("Task Title:", task.title)
            print("Task Status:", task.status)
            print("Task Total Cost:", task.total_cost, task.currency)
            print("Task Final Output length:", len(task.final_output) if task.final_output else 0)
        else:
            print("Task NOT found!")
            
        tx = db.query(TransactionModel).filter(TransactionModel.task_id == task_id).first()
        if tx:
            print("\nTransaction Record:")
            print("  TX ID:", tx.id)
            print("  User ID:", tx.user_id)
            print("  PayPal Order ID:", tx.paypal_order_id)
            print("  PayPal Capture ID:", tx.paypal_capture_id)
            print("  Amount:", tx.amount, tx.currency)
            print("  Payment Status:", tx.payment_status)
            print("  Provider:", tx.provider)
            print("  Created At:", tx.created_at)
            print("  Updated At:", tx.updated_at)
        else:
            print("Transaction NOT found!")

        steps = db.query(TaskStepModel).filter(TaskStepModel.task_id == task_id).all()
        print("\nTask Steps count:", len(steps))
        for s in steps:
            print(f"  Step [{s.status}]: {s.step_name} (Agent: {s.assigned_agent_id})")

if __name__ == "__main__":
    asyncio.run(verify_test2())
