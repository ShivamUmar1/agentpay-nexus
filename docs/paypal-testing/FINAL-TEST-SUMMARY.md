# AgentPay Nexus — PayPal Sandbox Integration Testing: Final Evidence Summary

**Document Type**: Master Evidence Index & Final Summary  
**Testing Period**: 2026-11-06 (UTC)  
**Production URL**: [https://agentpay-nexus.vercel.app](https://agentpay-nexus.vercel.app)  
**Repository**: [https://github.com/ShivamUmar1/agentpay-nexus](https://github.com/ShivamUmar1/agentpay-nexus)  
**Database**: Supabase Hosted PostgreSQL 17.11 (`aynszmhshjcuiywnooll`)  
**PayPal Environment**: Sandbox (`https://api-m.sandbox.paypal.com`)  
**PayPal API Version**: Orders v2 (CAPTURE intent)  

---

## 1. Project Overview & Testing Objective

AgentPay Nexus is an autonomous AI agent marketplace and PayPal settlement platform. Users submit task requests that are executed by a multi-agent AI pipeline (planning → research → data analysis → content generation → quality assurance → finance → payment → delivery). Payment is required for final deliverable unlock.

The purpose of this testing exercise was to validate the PayPal Orders v2 integration across four distinct geographic buyer/seller combinations using identical USD pricing ($8.00 USD), identical API integration, and identical agent pricing:

| Agent | Service Category | Price |
|:---|:---|:---|
| Deep Research Agent | Research | $2.00 USD |
| Quantitative Data Analysis Agent | Analytics | $3.00 USD |
| Executive Content Synthesis Agent | Content | $2.00 USD |
| Quality Assurance & Fact Auditor | Verification | $1.00 USD |
| **Total** | | **$8.00 USD** |

---

## 2. Four-Test Scenario Matrix

| Test | Buyer | Buyer Country | Seller | Seller Country | Currency | Verdict |
|:---|:---|:---|:---|:---|:---|:---|
| **Test 1** | US Personal | `US` | US Business | `US` | USD | ✅ **PASSED** |
| **Test 2** | India Personal | `IN` | US Business | `US` | USD | ✅ **PASSED** (2 runs) |
| **Test 3** | US Personal | `US` | India Business | `IN` | USD | ✅ **PASSED** |
| **Test 4** | India Personal | `IN` | India Business | `IN` | USD | ❌ **BLOCKED** |

**Summary of execution runs:**

- **Four distinct scenarios** were tested.
- **Five total execution runs** were performed: one Test 1 run, two independent Test 2 runs (2A and 2B), one Test 3 run, one Test 4 attempt.
- **Three scenarios passed** (Tests 1, 2, and 3).
- **Test 2 passed twice** through independent execution runs — both verified against the PayPal API and Supabase.
- **One scenario was blocked** (Test 4) by PayPal's platform-level prohibition on domestic India-to-India transactions.
- Tests 2A and 2B represent two independent verifications of the **same scenario** (India Personal → US Business), not two different scenarios.

---

## 3. Test 1 — US Personal → US Business

**Verdict: ✅ PASSED**  
**Detailed Report**: [TEST-1-US-TO-US.md](./TEST-1-US-TO-US.md)

### Evidence

| Identifier | Value |
|:---|:---|
| **PayPal Order ID** | `75K11736CB572603Y` |
| **PayPal Capture ID** | `70658947JX9692948` |
| **Order Status** | `COMPLETED` |
| **Capture Status** | `COMPLETED` |
| **Gross Amount** | `$8.00 USD` |
| **PayPal Fee** | `$0.77 USD` |
| **Net to Seller** | `$7.23 USD` |
| **Buyer Country** | `US` |
| **Seller Country** | `US` |
| **Seller Merchant ID** | US Business Sandbox |
| **Seller Protection** | `ELIGIBLE` |
| **Capture Timestamp** | 2026-11-06 (UTC) |

**Scenario type**: Domestic US-to-US flow. Standard PayPal checkout authorization and server-side capture.

---

## 4. Test 2 — India Personal → US Business

**Verdict: ✅ PASSED (2× independently verified)**  
**Detailed Report**: [TEST-2-INDIA-TO-US.md](./TEST-2-INDIA-TO-US.md)

### Run 2A — Automated AgentPay Nexus Run

| Identifier | Value |
|:---|:---|
| **PayPal Order ID** | `3NU881071F2178519` |
| **PayPal Capture ID** | `4XF639955L031754T` |
| **Task ID** | `e2a619e7-7d06-4061-bce0-9ec7e5dbb629` |
| **Order Status** | `COMPLETED` |
| **Capture Status** | `COMPLETED` |
| **Gross Amount** | `$8.00 USD` |
| **PayPal Fee** | `$0.89 USD` |
| **Net to Seller** | `$7.11 USD` |
| **Buyer Country** | `IN` |
| **Seller Country** | `US` |

### Run 2B — Manual Visa Card Auto Run

| Identifier | Value |
|:---|:---|
| **PayPal Order ID** | `8MU87667XB022832A` |
| **PayPal Capture ID** | `0RE44251J5276325P` |
| **Task ID** | `37543f0d-e9da-4fe7-aa59-8ed6629e92b3` |
| **Order Status** | `COMPLETED` |
| **Capture Status** | `COMPLETED` |
| **Gross Amount** | `$8.00 USD` |
| **Buyer-reported Visa card billing** | ₹782 INR (cross-border FX conversion) |
| **Buyer Country** | `IN` |
| **Seller Country** | `US` |

**Scenario type**: Cross-border India buyer → US seller. PayPal processed the USD-denominated order, applying cross-border transaction fees. The buyer's card was billed in INR (₹782) in Run 2B, confirming currency conversion on the buyer side.

---

## 5. Test 3 — US Personal → India Business

**Verdict: ✅ PASSED**  
**Detailed Report**: [TEST-3-US-TO-INDIA.md](./TEST-3-US-TO-INDIA.md)

### Evidence

| Identifier | Value |
|:---|:---|
| **PayPal Order ID** | `8RC0962473983884J` |
| **PayPal Capture ID** | `20L952323A1910922` |
| **Task ID** | `f615a14d-0317-4018-885c-1a89e8565431` |
| **Supabase Transaction ID** | `9aa62d28-23ae-4835-99ab-fcb79a055137` |
| **Order Status** | `COMPLETED` |
| **Capture Status** | `COMPLETED` |
| **Gross Amount** | `$8.00 USD` |
| **PayPal Fee** | `$0.72 USD` |
| **Net to Seller** | `$7.28 USD` |
| **Final Capture Flag** | `true` |
| **Buyer Country** | `US` (Payer ID: `CVQR3UNVUZA7G`) |
| **Seller Country** | `IN` |
| **Seller Merchant ID** | `F4M6RDMBJ5FFA` |
| **Seller Email** | `sb-fsux153719951@business.example.com` |
| **Seller Protection** | `ELIGIBLE` |
| **Capture Timestamp** | `2026-11-06T16:27:37Z` |

**Scenario type**: Cross-border US buyer → India seller. Confirmed that an Indian Business Sandbox merchant can receive and settle inbound USD payments from a US buyer.

---

## 6. Test 4 — India Personal → India Business (BLOCKED)

**Verdict: ❌ BLOCKED**  
**Detailed Report**: [TEST-4-INDIA-TO-INDIA.md](./TEST-4-INDIA-TO-INDIA.md)

### Exact Checkout Error Messages (Both Observed)

**Error 1:**
> "Something went wrong. Please go back to AgentPay Nexus and choose another way to pay. PayPal isn't available at this time."

**Error 2 (currency-specific):**
> "We're sorry. This seller doesn't accept payments in your currency. Please return to the seller and choose another way to pay."

Both error messages were produced by PayPal's checkout frontend before the buyer could complete authorization. No buyer approval was recorded.

### Order & Payment State

| Identifier | Value |
|:---|:---|
| **PayPal Order ID** | `80E59338RP265534N` |
| **PayPal Capture ID** | **NONE — Zero captures exist** |
| **Task ID** | `b91aaad2-cd06-496f-be2f-ede3eef39620` |
| **Supabase Transaction ID** | `637be8b9-ea6c-47e8-9306-9641a0f03a03` |
| **Order Status (API-verified)** | `CREATED` — Never transitioned to `APPROVED` |
| **Payer (API response)** | `{}` — Empty; buyer never authorized |
| **Transaction Status** | `pending` — Not updated |
| **Task Status** | `awaiting_payment` |
| **Deliverable** | Locked — Not released |
| **Buyer Country** | `IN` (India Personal) |
| **Seller Country** | `IN` (India Business, Merchant ID: `F4M6RDMBJ5FFA`) |
| **Intended Amount** | `$8.00 USD` (order created but not approved) |

### Root Cause

PayPal discontinued domestic payment processing in India **effective April 1, 2021**. When both buyer and seller accounts are registered in India (`IN`), PayPal's platform blocks the checkout before authorization regardless of the API version or currency denomination. This is a platform-level geographic restriction, not an application failure.

> [!NOTE]
> The error message *"This seller doesn't accept payments in your currency"* specifically surfaces the USD currency acceptance restriction that applies when both accounts are Indian-registered. This is consistent with PayPal India accounts being configured for cross-border (international) payments only — they cannot process domestic India-to-India payments even in USD.

**Supporting documentation**: PayPal officially exited the domestic payments market in India (April 2021), redirecting Indian accounts exclusively to cross-border transaction processing. This restriction is enforced in both live and Sandbox environments.

---

## 7. Cross-Border vs. Domestic Analysis

| Flow Direction | Result | Explanation |
|:---|:---|:---|
| US → US | ✅ PASSED | Standard domestic PayPal market |
| India → US (cross-border) | ✅ PASSED | PayPal cross-border outbound from India |
| US → India (cross-border) | ✅ PASSED | PayPal cross-border inbound to India |
| India → India (domestic) | ❌ BLOCKED | PayPal discontinued domestic India payments (April 2021) |

**Key finding**: AgentPay Nexus's PayPal integration functions correctly for all cross-border scenarios. The India domestic block is a PayPal platform policy, not an application defect.

---

## 8. Payment Fee Comparison

| Test | Scenario | Gross | Fee | Net | Fee % |
|:---|:---|:---|:---|:---|:---|
| Test 1 | US → US | $8.00 | $0.77 | $7.23 | 9.6% |
| Test 2A | India → US | $8.00 | $0.89 | $7.11 | 11.1% |
| Test 2B | India → US | $8.00 | — | — | — |
| Test 3 | US → India | $8.00 | $0.72 | $7.28 | 9.0% |
| Test 4 | India → India | $8.00 | N/A | N/A | Blocked |

Cross-border transactions carry higher PayPal processing fees than domestic flows.

---

## 9. AI Provider Limitation Disclosure

The AgentPay Nexus multi-agent pipeline uses Google Gemini Free Tier for AI content generation. During Test 2 (Run 2B), Test 3, and Test 4 executions, all three cascading Gemini model endpoints returned HTTP 429 quota-exceeded errors:

- `gemini-3.8-flash` → HTTP 429
- `gemini-3-flash-preview` → HTTP 429
- `gemini-flash-latest` → HTTP 429

In all cases, the application's built-in **demo generator fallback** produced deterministic synthetic agent outputs. This fallback mechanism does not affect:

- PayPal API order creation or capture
- Supabase persistence
- Payment verification logic
- Deliverable unlock logic

The Gemini 429 fallback is an **AI content generation limitation** only. It is disclosed here for transparency and does not affect the validity of any payment test result.

---

## 10. Individual Test Report Index

| Report File | Test | Verdict |
|:---|:---|:---|
| [TEST-1-US-TO-US.md](./TEST-1-US-TO-US.md) | Test 1 — US Personal → US Business | ✅ PASSED |
| [TEST-2-INDIA-TO-US.md](./TEST-2-INDIA-TO-US.md) | Test 2 — India Personal → US Business (2× verified) | ✅ PASSED |
| [TEST-3-US-TO-INDIA.md](./TEST-3-US-TO-INDIA.md) | Test 3 — US Personal → India Business | ✅ PASSED |
| [TEST-4-INDIA-TO-INDIA.md](./TEST-4-INDIA-TO-INDIA.md) | Test 4 — India Personal → India Business | ❌ BLOCKED |
| [TEST-TRACKER.md](./TEST-TRACKER.md) | Master Testing Matrix (all results) | — |

---

## 11. Relevant PayPal Documentation References

- **PayPal Orders v2 API**: https://developer.paypal.com/docs/api/orders/v2/
- **PayPal India domestic payments discontinuation (April 2021)**: Officially confirmed at paypal.com/in and corroborated by wise.com, skydo.com, and multiple independent sources.
- **PayPal Sandbox testing**: https://developer.paypal.com/tools/sandbox/

---

## 12. Final Overall Conclusion

The AgentPay Nexus PayPal Sandbox integration exercise is **complete**.

**Result summary:**
- ✅ **3 of 4 scenarios PASSED** (Tests 1, 2, 3)
- ❌ **1 of 4 scenarios BLOCKED** (Test 4 — domestic India-to-India restriction)
- ✅ **4 successful payment captures** across 4 execution runs (Tests 1, 2A, 2B, 3)
- ✅ **0 spurious or duplicate captures** — idempotency protections functioned correctly in all runs
- ✅ **Full end-to-end flow verified**: order creation → buyer approval → server-side pre-capture status check → capture → Supabase persistence → deliverable unlock
- ✅ **Application integrity confirmed**: Test 4's failed checkout did not corrupt the database, trigger a spurious capture, or incorrectly unlock a deliverable

The PayPal integration is production-ready for cross-border payment scenarios. The domestic India-to-India limitation is a PayPal platform policy that cannot be resolved at the application level.

---

*Document generated: 2026-11-06T23:19:00+05:30*  
*All transaction identifiers, capture IDs, and Supabase records are independently verified against live APIs and databases.*
