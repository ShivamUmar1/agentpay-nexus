import urllib.request
import json
import sys

def capture(task_id, order_id):
    print(f"Attempting server-side capture for PayPal Order: {order_id} on Task: {task_id}...")
    req = urllib.request.Request(
        "https://agentpay-nexus.vercel.app/api/payments/paypal/capture-order",
        data=json.dumps({"task_id": task_id, "order_id": order_id}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Verifier/1.0"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            print("\nCAPTURE SUCCESSFUL!")
            print(f"Capture ID: {data.get('capture_id')}")
            print(f"Status:     {data.get('status')}")
            print(f"Amount:     ${data.get('amount')} {data.get('currency')}")
            print(f"Provider:   {data.get('provider')}")
            print(f"Message:    {data.get('message')}")
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"\nHTTP {e.code}: {body}")
        return False

if __name__ == "__main__":
    task_id = sys.argv[1] if len(sys.argv) > 1 else "ccf38662-8f68-47be-ba65-7ada6a582dde"
    order_id = sys.argv[2] if len(sys.argv) > 2 else "5T221767YN836201T"
    capture(task_id, order_id)

