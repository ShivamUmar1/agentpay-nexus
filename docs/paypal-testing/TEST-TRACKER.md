# AgentPay Nexus — PayPal Sandbox Integration Testing Master Tracker

**Last Updated**: 2026-11-06T23:14:00+05:30  
**Production URL**: [https://agentpay-nexus.vercel.app](https://agentpay-nexus.vercel.app)  
**Database**: Supabase Hosted PostgreSQL 17.11 (`aynszmhshjcuiywnooll`)  
**AI Orchestration**: Google Gemini Free Tier (`gemini-3.8-flash` cascade)  

---

## Master Testing Matrix

| Test | Buyer | Seller | Currency | Status | Details / Documentation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Test 1** | US Personal | US Business | USD | **PASSED — $8 captured** | Verified Order `75K11736CB572603Y`, Capture `70658947JX9692948` ($8.00 USD). Domestic US flow. [TEST-1-US-TO-US.md](./TEST-1-US-TO-US.md) |
| **Test 2** | India Personal | US Business | USD | **PASSED (2x verified — $8 captured)** | Passed twice:<br>1. **Run 2A (Automated Run)**: Order `3NU881071F2178519`, Capture `4XF639955L031754T` ($8.00 USD).<br>2. **Run 2B (Manual Visa Auto Run)**: Order `8MU87667XB022832A`, Capture `0RE44251J5276325P` ($8.00 USD / user-reported Visa card billing ₹782 INR). [TEST-2-INDIA-TO-US.md](./TEST-2-INDIA-TO-US.md) |
| **Test 3** | US Personal | India Business | USD | **PASSED — $8 captured** | Order `8RC0962473983884J`, Capture `20L952323A1910922` ($8.00 USD). Inbound cross-border flow. [TEST-3-US-TO-INDIA.md](./TEST-3-US-TO-INDIA.md) |
| **Test 4** | India Personal | India Business | USD | **BLOCKED — Checkout rejected** | Order `80E59338RP265534N` created ($8.00 USD). PayPal rejected checkout before buyer authorization: *"Something went wrong. PayPal isn't available at this time."* No capture. Order status: `CREATED`. Tx status: `pending`. Deliverable: locked. Root cause: PayPal prohibits domestic India-to-India transactions (policy effective April 1, 2021). [TEST-4-INDIA-TO-INDIA.md](./TEST-4-INDIA-TO-INDIA.md) |

---

## Test Execution Guidelines & Security Rules

1. **Sandbox Only**: All tests are strictly executed in PayPal Sandbox environment (`https://api-m.sandbox.paypal.com`).
2. **Credential Safety**: Secrets, passwords, client secrets, and bearer tokens are strictly forbidden from tracking documents and Git repositories.
3. **Evidence Preservation**: Prior test records, database entries, orders, and captures must never be modified, deleted, reversed, or reused.
4. **Independent Verification**: A test may only be marked **PASSED** after direct programmatic verification against PayPal REST APIs and Supabase Hosted PostgreSQL.
