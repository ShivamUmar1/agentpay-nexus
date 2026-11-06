# Test 2 Evidence — Indian Personal Buyer to US Business Seller

**Test Status**: **IN PROGRESS (Awaiting Buyer Approval)**  
**Order Creation Timestamp**: 2026-11-06 14:48:25 UTC (20:18:25 IST)  
**Production URL**: [https://agentpay-nexus.vercel.app](https://agentpay-nexus.vercel.app)  
**Deployment Commit**: `34167b0` on `main`  
**Database**: Supabase Hosted PostgreSQL 17.11 (`aynszmhshjcuiywnooll`)  

---

## 1. Test Objective

Determine whether an Indian Personal Sandbox buyer can successfully purchase an AgentPay Nexus autonomous service from the existing US Business Sandbox merchant using a USD-denominated PayPal order.

This examines cross-border payment processing from an Indian consumer to a US business entity, inspecting:
- Whether PayPal Sandbox permits an Indian buyer to authorize a native USD order.
- How PayPal presents checkout funding sources (e.g. PayPal Balance, linked card, automatic INR-to-USD currency conversion).
- Whether cross-border export/import restrictions or currency conversion barriers emerge during buyer approval.

---

## 2. Participant Accounts & Configuration

| Role | Property | Value |
| :--- | :--- | :--- |
| **Buyer** | Account Type | Personal Sandbox Account |
| **Buyer** | Registered Country | `IN` (India) |
| **Buyer** | Native Currency | `INR` (Indian Rupee) |
| **Seller / Merchant** | Account Type | Business Sandbox Account (`sb-jffuj53655931@business.example.com`) |
| **Seller / Merchant** | Merchant ID | `U6DA8TWKPA2HQ` |
| **Seller / Merchant** | Registered Country | `US` (United States) |
| **Application Mode** | Operating Mode | `sandbox` (`https://api-m.sandbox.paypal.com`) |
| **Transaction Currency** | Order Currency | `USD` |

---

## 3. Task & Order Identifiers

| Parameter | Value |
| :--- | :--- |
| **Task ID** | `e2a619e7-7d06-4061-bce0-9ec7e5dbb629` |
| **Task Title** | India EV Market Research & Strategy |
| **Task Budget** | `$10.00 USD` |
| **Calculated Invoice Amount** | `$8.00 USD` |
| **PayPal Order ID** | `3NU881071F2178519` |
| **Order Status on PayPal** | `CREATED` |
| **Order Intent** | `CAPTURE` |
| **Payee Email** | `sb-jffuj53655931@business.example.com` |
| **Payee Merchant ID** | `U6DA8TWKPA2HQ` |
| **Approval URL** | [https://www.sandbox.paypal.com/checkoutnow?token=3NU881071F2178519](https://www.sandbox.paypal.com/checkoutnow?token=3NU881071F2178519) |

---

## 4. Invoice Line-Item Breakdown (Trusted Backend Calculation)

Calculated by `FinanceAgent` from subtask execution steps in Supabase PostgreSQL:

| Agent | Category | Subtask Scope | Amount |
| :--- | :--- | :--- | :--- |
| **Deep Research Agent** | Research | 2W, 3W, 4W market share and regulatory framework | `$2.00 USD` |
| **Quantitative Data Analysis Agent** | Analytics | Growth CAGR, competitor matrix & volume forecasting | `$3.00 USD` |
| **Executive Content Synthesis Agent** | Content | Strategic roadmap and executive summary | `$2.00 USD` |
| **Quality Assurance & Fact Auditor** | Verification | Validation against verified sources & metrics | `$1.00 USD` |
| **Subtotal** | | | **$8.00 USD** |
| **Platform Fee** | | 0% promotional hackathon tier | **$0.00 USD** |
| **Total Invoice** | | | **$8.00 USD** |

---

## 5. Live Production Order Verification

`GET https://agentpay-nexus.vercel.app/api/payments/paypal/order/3NU881071F2178519`  
**HTTP Status**: `200 OK`

```json
{
  "order_id": "3NU881071F2178519",
  "status": "CREATED",
  "intent": "CAPTURE",
  "amount": {
    "currency_code": "USD",
    "value": "8.00",
    "breakdown": {
      "item_total": {
        "currency_code": "USD",
        "value": "8.00"
      }
    }
  },
  "payee": {
    "email_address": "sb-jffuj53655931@business.example.com",
    "merchant_id": "U6DA8TWKPA2HQ",
    "display_data": {
      "brand_name": "AgentPay Nexus"
    }
  }
}
```

---

## 6. Execution Checkpoint & Next Action

- **Current State**: Order created, persisted in Supabase PostgreSQL, awaiting buyer approval.
- **Buyer Action Required**:
  1. Open checkout link: [https://www.sandbox.paypal.com/checkoutnow?token=3NU881071F2178519](https://www.sandbox.paypal.com/checkoutnow?token=3NU881071F2178519)
  2. Authenticate with the **Indian Personal Sandbox buyer account**.
  3. Inspect funding options (Balance, Cards, Currency Conversion).
  4. Complete or report outcome.
- **Subsequent Actions**:
  - If approved: System automatically invokes server-side pre-verification and capture.
  - If rejected: Record exact error message, error code, and PayPal debug ID.
