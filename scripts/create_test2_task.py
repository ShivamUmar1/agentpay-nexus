import asyncio
import os
import sys
import time
import httpx
from dotenv import dotenv_values

PROD_URL = "https://agentpay-nexus.vercel.app"

async def create_and_advance_test2():
    print("=== STARTING TEST 2 TASK CREATION & PIPELINE ADVANCE ===\n")
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        # Step 1: Create Task
        payload = {
            "title": "India EV Market Research & Strategy",
            "description": "Prepare a concise market research summary about India's electric vehicle industry, including growth trends, major competitors and opportunities.",
            "budget": 10.0,
            "currency": "USD",
            "constraints": "Highlight 2W, 3W, 4W market share and include policy impact like FAME-II and PLI"
        }
        
        print("Submitting task to production...")
        res = await client.post(f"{PROD_URL}/api/tasks", json=payload)
        print("Create Task Status Code:", res.status_code)
        if res.status_code != 200:
            print("Error creating task:", res.text)
            return
            
        task_data = res.json()
        task_id = task_data["id"]
        print("New Task ID:", task_id)
        print("Task Title:", task_data["title"])
        print("Initial Status:", task_data["status"])
        print("Execution Plan Steps:", len(task_data.get("steps", [])))
        for s in task_data.get("steps", []):
            print(f"  Step: {s['step_name']} (Agent: {s.get('assigned_agent_id')})")

        # Step 2: Advance Task through workflow steps until awaiting_payment
        print("\n--- Advancing task through multi-agent pipeline ---")
        max_steps = 15
        step_count = 0
        current_status = task_data["status"]
        
        while current_status not in ["awaiting_payment", "completed", "failed"] and step_count < max_steps:
            step_count += 1
            print(f"\n[Step {step_count}] Advancing pipeline for task {task_id}...")
            adv_res = await client.post(f"{PROD_URL}/api/tasks/{task_id}/advance")
            print("  Advance HTTP:", adv_res.status_code)
            if adv_res.status_code != 200:
                print("  Advance error:", adv_res.text)
                break
            adv_data = adv_res.json()
            current_status = adv_data.get("status", current_status)
            print(f"  Current Task Status: {current_status}")
            print(f"  Action message: {adv_data.get('message')}")
            if current_status == "awaiting_payment":
                print("  => Reached invoice & awaiting payment stage!")
                break
            await asyncio.sleep(2)

        # Step 3: Get Task and Invoice
        print("\n--- Fetching Invoice & Cost Details ---")
        inv_res = await client.get(f"{PROD_URL}/api/payments/invoice/{task_id}")
        print("Invoice HTTP:", inv_res.status_code)
        inv_data = inv_res.json()
        print("Invoice Subtotal:", inv_data.get("subtotal"))
        print("Invoice Platform Fee:", inv_data.get("platform_fee"))
        print("Invoice Total Amount:", inv_data.get("total_amount"), inv_data.get("currency"))
        items = inv_data.get("items", [])
        print(f"Invoice Line Items ({len(items)}):")
        for item in items:
            print(f"  - {item.get('agent_name')} ({item.get('category')}): ${item.get('unit_price')} USD")

        # Step 4: Create PayPal Sandbox Order
        print("\n--- Creating Fresh PayPal Orders v2 Order ---")
        order_payload = {
            "task_id": task_id,
            "return_url": f"{PROD_URL}/tasks/{task_id}?approved=true",
            "cancel_url": f"{PROD_URL}/tasks/{task_id}?cancelled=true"
        }
        order_res = await client.post(f"{PROD_URL}/api/payments/paypal/create-order", json=order_payload)
        print("Create Order HTTP:", order_res.status_code)
        if order_res.status_code != 200:
            print("Create Order Error:", order_res.text)
            return
            
        order_data = order_res.json()
        print("PayPal Order ID:", order_data.get("order_id"))
        print("Status:", order_data.get("status"))
        print("Amount:", order_data.get("amount"), order_data.get("currency"))
        print("Approval URL:", order_data.get("approval_url"))
        
        # Step 5: Direct Verification of Order on PayPal
        print("\n--- Direct PayPal Verification of Test 2 Order ---")
        detail_res = await client.get(f"{PROD_URL}/api/payments/paypal/order/{order_data.get('order_id')}")
        print("Direct PayPal Query HTTP:", detail_res.status_code)
        detail_data = detail_res.json()
        print("Order Status:", detail_data.get("status"))
        print("Payee details:", detail_data.get("payee"))
        print("Order Amount:", detail_data.get("amount"))

if __name__ == "__main__":
    asyncio.run(create_and_advance_test2())
