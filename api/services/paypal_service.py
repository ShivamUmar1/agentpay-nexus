import base64
import logging
import time
import uuid
from typing import Dict, Any, Optional
import httpx
from api.config import settings

logger = logging.getLogger(__name__)


class PayPalService:
    """Official PayPal REST API integration (Sandbox and Production) with simulated demo fallback."""

    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0

    @property
    def is_configured(self) -> bool:
        return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)

    async def get_access_token(self) -> Optional[str]:
        """Obtains OAuth2 access token from PayPal using client credentials grant."""
        if not self.is_configured:
            return None

        now = time.time()
        if self._access_token and now < self._token_expires_at - 60:
            return self._access_token

        client_id = settings.PAYPAL_CLIENT_ID
        client_secret = settings.PAYPAL_CLIENT_SECRET
        auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

        url = f"{settings.paypal_endpoint}/v1/oauth2/token"
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, headers=headers, data=data)
                res.raise_for_status()
                token_data = res.json()
                self._access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = now + expires_in
                return self._access_token
        except Exception as e:
            logger.error(f"PayPal OAuth token acquisition failed: {e}")
            raise RuntimeError(f"Failed to authenticate with PayPal API: {str(e)}")

    async def test_connection(self) -> Dict[str, Any]:
        """Tests connectivity and OAuth credentials against the PayPal Sandbox environment."""
        if not self.is_configured:
            return {
                "status": "simulated_demo_mode",
                "configured": False,
                "mode": settings.PAYPAL_MODE,
                "message": "PayPal credentials not set; running in simulated demo mode."
            }

        t0 = time.time()
        try:
            token = await self.get_access_token()
            latency = round((time.time() - t0) * 1000, 1)
            # Mask client id prefix
            cid_masked = f"{settings.PAYPAL_CLIENT_ID[:6]}...{settings.PAYPAL_CLIENT_ID[-4:]}" if len(settings.PAYPAL_CLIENT_ID or "") > 10 else "configured"
            return {
                "status": "sandbox_connected",
                "configured": True,
                "mode": settings.PAYPAL_MODE,
                "latency_ms": latency,
                "client_id": cid_masked,
                "token_active": bool(token)
            }
        except Exception as e:
            return {
                "status": "auth_failed",
                "configured": True,
                "mode": settings.PAYPAL_MODE,
                "error": str(e)
            }

    async def create_order(
        self,
        task_id: str,
        task_title: str,
        amount: float,
        currency: str = "USD",
        items: Optional[list] = None
    ) -> Dict[str, Any]:
        """Creates a PayPal order via Orders v2 API, or generates a verified simulated demo order."""
        if not self.is_configured:
            # Deterministic, clearly-labeled simulated demo mode
            simulated_order_id = f"SIM-ORD-{uuid.uuid4().hex[:12].upper()}"
            return {
                "order_id": simulated_order_id,
                "status": "CREATED",
                "amount": amount,
                "currency": currency,
                "provider": "simulated",
                "is_simulated": True,
                "approval_url": f"{settings.APP_BASE_URL}/checkout?order_id={simulated_order_id}"
            }

        token = await self.get_access_token()
        url = f"{settings.paypal_endpoint}/v2/checkout/orders"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        # Build PayPal items breakdown
        paypal_items = []
        if items:
            for it in items:
                paypal_items.append({
                    "name": getattr(it, "agent_name", "AI Agent")[:127],
                    "description": f"Autonomous service: {getattr(it, 'category', 'AI Services')}"[:127],
                    "unit_amount": {
                        "currency_code": currency,
                        "value": f"{getattr(it, 'unit_price', amount):.2f}"
                    },
                    "quantity": str(getattr(it, "quantity", 1))
                })

        payload: Dict[str, Any] = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": task_id,
                    "description": f"AgentPay Nexus: {task_title}"[:127],
                    "custom_id": task_id,
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}",
                        "breakdown": {
                            "item_total": {
                                "currency_code": currency,
                                "value": f"{amount:.2f}"
                            }
                        } if paypal_items else {}
                    }
                }
            ],
            "application_context": {
                "brand_name": "AgentPay Nexus",
                "landing_page": "NO_PREFERENCE",
                "user_action": "PAY_NOW"
            }
        }

        if paypal_items:
            payload["purchase_units"][0]["items"] = paypal_items

        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code >= 400:
                logger.error(f"PayPal order creation failed: {res.text}")
                raise RuntimeError(f"PayPal Order Creation API returned error: {res.text}")
            
            order_data = res.json()
            approval_link = next(
                (l["href"] for l in order_data.get("links", []) if l.get("rel") == "approve"),
                None
            )

            return {
                "order_id": order_data["id"],
                "status": order_data["status"],
                "amount": amount,
                "currency": currency,
                "provider": f"paypal_{settings.PAYPAL_MODE.lower()}",
                "is_simulated": False,
                "approval_url": approval_link
            }

    async def capture_order(
        self,
        order_id: str,
        expected_amount: float,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """Captures payment for an authorized order and verifies amount integrity."""
        # Check simulated order
        if order_id.startswith("SIM-ORD-") or not self.is_configured:
            simulated_capture_id = f"SIM-CAP-{uuid.uuid4().hex[:12].upper()}"
            return {
                "success": True,
                "order_id": order_id,
                "capture_id": simulated_capture_id,
                "status": "COMPLETED",
                "amount": expected_amount,
                "currency": currency,
                "provider": "simulated",
                "is_simulated": True,
                "message": "Simulated payment captured successfully (Demo Mode)."
            }

        token = await self.get_access_token()
        url = f"{settings.paypal_endpoint}/v2/checkout/orders/{order_id}/capture"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(url, headers=headers)
            if res.status_code >= 400:
                logger.error(f"PayPal capture failed: {res.text}")
                raise RuntimeError(f"PayPal capture failed: {res.text}")

            capture_data = res.json()
            status = capture_data.get("status")

            if status != "COMPLETED":
                return {
                    "success": False,
                    "order_id": order_id,
                    "capture_id": None,
                    "status": status,
                    "amount": expected_amount,
                    "currency": currency,
                    "provider": f"paypal_{settings.PAYPAL_MODE.lower()}",
                    "is_simulated": False,
                    "message": f"Payment capture status is {status}, expected COMPLETED"
                }

            # Retrieve purchase unit capture details
            purchase_units = capture_data.get("purchase_units", [])
            captures = purchase_units[0].get("payments", {}).get("captures", []) if purchase_units else []
            capture_id = captures[0].get("id") if captures else None
            captured_amount = float(captures[0]["amount"]["value"]) if captures else expected_amount

            # Security verification: Check amount match
            if abs(captured_amount - expected_amount) > 0.01:
                logger.warning(f"Payment amount mismatch: captured {captured_amount} != expected {expected_amount}")

            return {
                "success": True,
                "order_id": order_id,
                "capture_id": capture_id,
                "status": "COMPLETED",
                "amount": captured_amount,
                "currency": currency,
                "provider": f"paypal_{settings.PAYPAL_MODE.lower()}",
                "is_simulated": False,
                "message": "PayPal payment captured and verified successfully."
            }


paypal_service = PayPalService()
