# Test 1 Evidence — Domestic US Sandbox End-to-End Settlement

**Test Status**: **PASSED**  
**Execution Date & Time**: 2026-11-06 14:28:44 UTC (19:58:44 IST)  
**Production URL**: [https://agentpay-nexus.vercel.app](https://agentpay-nexus.vercel.app)  
**Deployment Commit**: `34167b0` (`chore(config): ignore all .env backups and optimize non-interactive Vercel env sync`)  
**Deployment ID**: `dpl_Bsu1vZCrwuAoqpDRcqbxD8EiQq8j`  

---

## 1. Test Objective

Validate the complete end-to-end PayPal Orders v2 integration lifecycle for an autonomous multi-agent task execution on AgentPay Nexus within a domestic US Sandbox environment:
1. Automatic multi-agent task planning and subtask execution.
2. Trusted backend invoice generation for delivered agent work ($8.00 USD).
3. PayPal Orders v2 order creation with `CAPTURE` intent.
4. Seamless buyer authorization flow via official `rel=approve` HATEOAS redirect.
5. Server-side pre-verification of `APPROVED` order status directly against PayPal Orders v2 API.
6. Server-side capture execution (`POST /v2/checkout/orders/{id}/capture`).
7. Transaction persistence in Supabase Hosted PostgreSQL (`aynszmhshjcuiywnooll`).
8. Deliverable unlock and state advancement to `completed`.

---

## 2. Participant Accounts & Configuration

| Role | Property | Value |
| :--- | :--- | :--- |
| **Buyer** | Account Type | Personal Sandbox Account |
| **Buyer** | Country Code | `US` (United States) |
| **Buyer** | Funding Source | PayPal Balance / Sandbox Linked Card (USD) |
| **Seller / Merchant** | Account Type | Business Sandbox Account (`sb-jffuj53655931@business.example.com`) |
| **Seller / Merchant** | Merchant ID | `U6DA8TWKPA2HQ` |
| **Seller / Merchant** | Country Code | `US` (United States) |
| **Payment Protocol** | API Standard | PayPal REST API v2 (Orders v2 & Payments Captures v2) |
| **Environment** | Operating Mode | `sandbox` (`https://api-m.sandbox.paypal.com`) |

---

## 3. Transaction Identifiers & Financial Summary

| Identifier / Metric | Value |
| :--- | :--- |
| **Production Task ID** | `3fda270f-0680-4a03-a495-01782ac9b505` |
| **Task Title** | India EV Market Analysis and Growth Roadmap |
| **PayPal Order ID** | `75K11736CB572603Y` |
| **PayPal Capture ID** | `70658947JX9692948` |
| **Currency** | `USD` |
| **Gross Amount** | `$8.00 USD` |
| **PayPal Fee** | `$0.77 USD` |
| **Net Amount to Seller** | `$7.23 USD` |
| **Final Capture Flag** | `true` |
| **Seller Protection** | `ELIGIBLE` (`ITEM_NOT_RECEIVED`, `UNAUTHORIZED_TRANSACTION`) |

---

## 4. Independent PayPal API Verification Evidence

### A. Orders v2 API Query
`GET https://api-m.sandbox.paypal.com/v2/checkout/orders/75K11736CB572603Y`  
**HTTP Status**: `200 OK`

```json
{
  "id": "75K11736CB572603Y",
  "status": "COMPLETED",
  "intent": "CAPTURE",
  "purchase_units": [
    {
      "reference_id": "default",
      "amount": {
        "currency_code": "USD",
        "value": "8.00",
        "breakdown": {}
      },
      "payee": {
        "email_address": "sb-jffuj53655931@business.example.com",
        "merchant_id": "U6DA8TWKPA2HQ",
        "display_data": {
          "brand_name": "AgentPay Nexus"
        }
      },
      "payments": {
        "captures": [
          {
            "id": "70658947JX9692948",
            "status": "COMPLETED",
            "amount": {
              "currency_code": "USD",
              "value": "8.00"
            },
            "final_capture": true,
            "seller_protection": {
              "status": "ELIGIBLE",
              "dispute_categories": [
                "ITEM_NOT_RECEIVED",
                "UNAUTHORIZED_TRANSACTION"
              ]
            },
            "seller_receivable_breakdown": {
              "gross_amount": {
                "currency_code": "USD",
                "value": "8.00"
              },
              "paypal_fee": {
                "currency_code": "USD",
                "value": "0.77"
              },
              "net_amount": {
                "currency_code": "USD",
                "value": "7.23"
              }
            },
            "create_time": "2026-11-06T14:28:44Z",
            "update_time": "2026-11-06T14:28:44Z"
          }
        ]
      }
    }
  ]
}
```

### B. Payments Captures API Query
`GET https://api-m.sandbox.paypal.com/v2/payments/captures/70658947JX9692948`  
**HTTP Status**: `200 OK`

```json
{
  "id": "70658947JX9692948",
  "status": "COMPLETED",
  "amount": {
    "currency_code": "USD",
    "value": "8.00"
  },
  "final_capture": true,
  "seller_protection": {
    "status": "ELIGIBLE",
    "dispute_categories": [
      "ITEM_NOT_RECEIVED",
      "UNAUTHORIZED_TRANSACTION"
    ]
  },
  "seller_receivable_breakdown": {
    "gross_amount": {
      "currency_code": "USD",
      "value": "8.00"
    },
    "paypal_fee": {
      "currency_code": "USD",
      "value": "0.77"
    },
    "net_amount": {
      "currency_code": "USD",
      "value": "7.23"
    }
  },
  "create_time": "2026-11-06T14:28:44Z",
  "update_time": "2026-11-06T14:28:44Z"
}
```

---

## 5. Independent Supabase PostgreSQL Verification Evidence

**Host Database**: Supabase Hosted PostgreSQL 17.11 (`aynszmhshjcuiywnooll`)  
**Table**: `transactions` & `tasks`

```sql
SELECT id, user_id, task_id, paypal_order_id, paypal_capture_id, amount, currency, payment_status, provider, updated_at
FROM transactions
WHERE paypal_order_id = '75K11736CB572603Y';
```

**Retrieved Record**:
- **Transaction ID**: `0e28eb34-7a07-485e-8d17-657aebba2578`
- **User ID**: `user_guest_01`
- **Task ID**: `3fda270f-0680-4a03-a495-01782ac9b505`
- **PayPal Order ID**: `75K11736CB572603Y`
- **PayPal Capture ID**: `70658947JX9692948`
- **Amount**: `8.0`
- **Currency**: `USD`
- **Payment Status**: `completed`
- **Provider**: `paypal_sandbox`
- **Created At**: `2026-11-06 09:49:52.643758+00:00`
- **Updated At**: `2026-11-06 14:28:45.338923+00:00`

---

## 6. Task Completion & Deliverable Unlock Verification

- **Task Status**: `completed`
- **Total Cost**: `$8.00 USD`
- **Final Deliverable**: Unlocked (10,087 bytes of structured multi-agent market analysis, competitor roadmaps, and financial metrics).
- **Subtask Graph**: 8 / 8 nodes resolved successfully:
  1. `finance_calculation` (`agent_finance_05`) — COMPLETED
  2. `planning` (`agent_orchestrator_00`) — COMPLETED
  3. `research` (`agent_research_01`) — COMPLETED
  4. `data_analysis` (`agent_analysis_02`) — COMPLETED
  5. `content_generation` (`agent_content_03`) — COMPLETED
  6. `quality_assurance` (`agent_qa_04`) — COMPLETED
  7. `payment_approval` (`agent_payment_06`) — COMPLETED
  8. `final_delivery` (`agent_orchestrator_00`) — COMPLETED

---

## 7. Conclusion

Test 1 conclusively demonstrates that the AgentPay Nexus application, its client-side approval flow, server-side pre-capture status verification, Orders v2 capture mechanism, and Supabase persistent PostgreSQL storage operate with 100% fidelity in domestic US Sandbox settlement.

**Final Result**: **PASSED**
