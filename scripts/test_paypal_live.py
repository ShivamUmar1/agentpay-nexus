import asyncio
import sys
sys.path.insert(0, ".")

from api.services.paypal_service import paypal_service

async def test_paypal():
    print("Testing Real PayPal Sandbox Order Creation...")
    token = await paypal_service.get_access_token()
    print(f"OAuth Token Acquired: {token[:15]}... (Length: {len(token)})")

    order = await paypal_service.create_order(
        task_id="test_task_paypal_01",
        task_title="Test Market Research Order",
        amount=8.00,
        currency="USD"
    )
    print(f"PayPal Order ID:   {order.get('order_id')}")
    print(f"Status:            {order.get('status')}")
    print(f"Is Simulated:      {order.get('is_simulated')}")
    print(f"Provider:          {order.get('provider')}")
    print(f"Approval URL:      {order.get('approval_url')}")
    assert not order.get('is_simulated'), "Expected REAL PayPal Sandbox order, got simulated!"
    print("\nSUCCESS: Real PayPal Sandbox order successfully created on PayPal's servers!")

if __name__ == "__main__":
    asyncio.run(test_paypal())

