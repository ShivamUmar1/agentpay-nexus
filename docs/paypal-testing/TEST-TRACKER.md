# AgentPay Nexus — PayPal Sandbox Integration Testing Master Tracker

**Last Updated**: 2026-11-06T20:15:00+05:30  
**Production URL**: [https://agentpay-nexus.vercel.app](https://agentpay-nexus.vercel.app)  
**Database**: Supabase Hosted PostgreSQL 17.11 (`aynszmhshjcuiywnooll`)  
**AI Orchestration**: Google Gemini Free Tier (`gemini-3.8-flash` cascade)  

---

## Master Testing Matrix

| Test | Buyer | Seller | Currency | Status | Details / Documentation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Test 1** | US Personal | US Business | USD | **PASSED — $8 captured** | Verified Order `75K11736CB572603Y`, Capture `70658947JX9692948` ($8.00 USD). [TEST-1-US-TO-US.md](./TEST-1-US-TO-US.md) |
| **Test 2** | India Personal | US Business | USD | **IN PROGRESS** | Cross-border India-to-US buyer flow. [TEST-2-INDIA-TO-US.md](./TEST-2-INDIA-TO-US.md) |
| **Test 3** | US Personal | India Business | USD | **NOT STARTED** | Cross-border US-to-India seller flow. |
| **Test 4** | India Personal | India Business | USD | **NOT STARTED** | Domestic India Sandbox flow. |

---

## Test Execution Guidelines & Security Rules

1. **Sandbox Only**: All tests are strictly executed in PayPal Sandbox environment (`https://api-m.sandbox.paypal.com`).
2. **Credential Safety**: Secrets, passwords, client secrets, and bearer tokens are strictly forbidden from tracking documents and Git repositories.
3. **Evidence Preservation**: Prior test records, database entries, orders, and captures must never be modified, deleted, reversed, or reused.
4. **Independent Verification**: A test may only be marked **PASSED** after direct programmatic verification against PayPal REST APIs and Supabase Hosted PostgreSQL.
