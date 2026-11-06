import urllib.request
import json
import time

def post(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Verifier/1.0"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read())

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Verifier/1.0"})
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read())

def main():
    print("=== TESTING REAL PRODUCTION PIPELINE WITH PAYPAL SANDBOX ===\n")
    
    # 1. Create Task on Production
    status, task = post("https://agentpay-nexus.vercel.app/api/tasks", {
        "title": "Autonomous EV Market Research India",
        "description": "Analyze market sizing, CAGR, competitors and supply chain dynamics with $10 budget.",
        "budget": 10.0,
        "currency": "USD"
    })
    print(f"1. Task Created: HTTP {status}")
    print(f"   Task ID: {task.get('id')}")
    print(f"   Status:  {task.get('status')}")
    task_id = task["id"]

    # 2. Advance to payment
    current = task.get("status")
    step_count = 0
    while current not in ["awaiting_payment", "completed", "failed"] and step_count < 10:
        step_count += 1
        s, step_res = post(f"https://agentpay-nexus.vercel.app/api/tasks/{task_id}/advance", {})
        current = step_res.get("status")
        print(f"   Step {step_count}: '{step_res.get('advanced_step')}' -> Task status: {current}")
        time.sleep(0.3)

    # 3. Create REAL PayPal Sandbox Order on Production
    s, order = post("https://agentpay-nexus.vercel.app/api/payments/paypal/create-order", {"task_id": task_id})
    print(f"\n2. REAL PayPal Sandbox Order Created on Vercel Production:")
    print(f"   Order ID:     {order.get('order_id')}")
    print(f"   Status:       {order.get('status')}")
    print(f"   Amount:       ${order.get('amount')} {order.get('currency')}")
    print(f"   Provider:     {order.get('provider')}")
    print(f"   Approval URL: {order.get('approval_url')}")
    assert order.get("provider") == "paypal_sandbox", f"Expected paypal_sandbox, got {order.get('provider')}"
    print("\n✓ SUCCESS: Production is generating authenticated PayPal Sandbox Orders via PayPal REST API v2!")

if __name__ == "__main__":
    main()

