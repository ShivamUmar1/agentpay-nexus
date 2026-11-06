import asyncio
import os
import sys
import time

# Ensure api is importable
sys.path.insert(0, ".")

from api.config import settings
from api.database import test_db_connection
from api.services.llm_provider import llm_provider
from api.services.paypal_service import paypal_service

async def run_diagnostics():
    print("=" * 65)
    print("AGENTPAY NEXUS — LIVE INTEGRATION DIAGNOSTIC SUITE")
    print("=" * 65)

    # 1. Database Diagnostic
    print("\n[1/3] Probing Database Connection...")
    db_res = test_db_connection()
    status = db_res.get("status")
    db_type = db_res.get("type")
    is_persistent = db_res.get("persistent")
    print(f"      Status:      {status.upper()}")
    print(f"      Engine:      {db_type}")
    print(f"      Persistent:  {is_persistent} ({'Hosted Supabase' if is_persistent else 'Local/Ephemeral'})")
    if "counts" in db_res:
        counts = db_res["counts"]
        print(f"      Counts:      {counts['agents']} agents, {counts['tasks']} tasks, {counts['transactions']} txs")
    if "error" in db_res:
        print(f"      Error:       {db_res['error']}")

    # 2. AI Reasoning Diagnostic (Gemini)
    print("\n[2/3] Probing AI Orchestration Engine (Google Gemini)...")
    ai_res = await llm_provider.test_connection()
    ai_status = ai_res.get("status")
    print(f"      Status:      {ai_status.upper()}")
    print(f"      Provider:    {ai_res.get('provider')}")
    print(f"      Model:       {ai_res.get('model')}")
    if "latency_ms" in ai_res:
        print(f"      Latency:     {ai_res['latency_ms']} ms")
    if "sample_response" in ai_res:
        print(f"      Sample:      '{ai_res['sample_response']}'")
    if "error" in ai_res:
        print(f"      Error:       {ai_res['error']}")

    # 3. PayPal Sandbox Payment Gateway
    print("\n[3/3] Probing PayPal Sandbox Payment Gateway...")
    pay_res = await paypal_service.test_connection()
    pay_status = pay_res.get("status")
    print(f"      Status:      {pay_status.upper()}")
    print(f"      Mode:        {pay_res.get('mode')}")
    print(f"      Configured:  {pay_res.get('configured')}")
    if "client_id" in pay_res:
        print(f"      Client ID:   {pay_res['client_id']}")
    if "latency_ms" in pay_res:
        print(f"      OAuth Ping:  {pay_res['latency_ms']} ms")
    if "error" in pay_res:
        print(f"      Error:       {pay_res['error']}")

    print("\n" + "=" * 65)
    all_live = (
        db_res.get("persistent") is True and
        ai_res.get("status") == "connected" and
        pay_res.get("status") == "sandbox_connected"
    )
    if all_live:
        print("ALL 3 EXTERNAL PRODUCTION INTEGRATIONS ARE 100% OPERATIONAL!")
    else:
        print("STATUS: Operating with fallback / demo modes for unconfigured services.")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(run_diagnostics())

