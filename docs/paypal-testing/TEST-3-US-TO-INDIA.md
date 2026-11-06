# Test 3 Evidence — Cross-Border US Personal Buyer to Indian Business Seller

**Test Status**: **PASSED**  
**Execution Date & Time**: 2026-11-06 16:27:37 UTC (21:57:37 IST)  
**Production URL**: [https://agentpay-nexus.vercel.app](https://agentpay-nexus.vercel.app)  
**Deployment Commit**: `34167b0` on `main`  
**Deployment ID**: `dpl_8RHxeC3V3PjTuXeiD1E9oikZg5E5`  
**Database**: Supabase Hosted PostgreSQL 17.11 (`aynszmhshjcuiywnooll`)  

---

## 1. Test Objective & Cross-Border Scope

Test whether a US Personal PayPal Sandbox buyer can successfully pay an Indian Business PayPal Sandbox seller through AgentPay Nexus for an autonomous multi-agent task execution denominated in USD.

This examines cross-border payment acceptance:
- **Direction**: United States (`US`) Personal Buyer &rarr; India (`IN`) Business Seller.
- **Currency**: `USD` ($8.00 USD).
- **Core Verification Focus**: Testing whether the Indian Business seller's PayPal Sandbox account can accept inbound cross-border USD payments under its current configuration, verifying international routing and currency settlement.
- **Execution Method**: Manual buyer approval through the production web UI followed by server-side payment capture.

---

## 2. Participant Accounts & Configuration

| Role | Property | Value |
| :--- | :--- | :--- |
| **Buyer** | Account Type | Personal Sandbox Account |
| **Buyer** | Registered Country | `US` (United States) |
| **Buyer** | Payer Account | `sb-yfhat53756342@personal.example.com` (Payer ID: `CVQR3UNVUZA7G`) |
| **Buyer** | Transaction Currency | `USD` |
| **Seller / Merchant** | Account Type | Business Sandbox Account (`sb-fsux153719951@business.example.com`) |
| **Seller / Merchant** | Merchant ID | `F4M6RDMBJ5FFA` |
| **Seller / Merchant** | Registered Country | `IN` (India) |
| **Payment Protocol** | API Standard | PayPal REST API v2 (Orders v2 with CAPTURE intent) |
| **Environment** | Operating Mode | `sandbox` (`https://api-m.sandbox.paypal.com`) |

---

## 3. Transaction Identifiers & Financial Summary

| Identifier / Metric | Value |
| :--- | :--- |
| **Production Task ID** | `f615a14d-0317-4018-885c-1a89e8565431` |
| **Task Title** | Test 3 - US to India Business Cross-Border Payment Verification |
| **Task Budget** | `$10.00 USD` |
| **PayPal Order ID** | `8RC0962473983884J` |
| **PayPal Capture ID** | `20L952323A1910922` |
| **Currency** | `USD` |
| **Gross Amount** | `$8.00 USD` |
| **PayPal Fee** | `$0.72 USD` |
| **Net Amount to Seller** | `$7.28 USD` |
| **Final Capture Flag** | `true` |
| **Seller Protection** | `ELIGIBLE` (`ITEM_NOT_RECEIVED`, `UNAUTHORIZED_TRANSACTION`) |
| **Supabase Transaction ID** | `9aa62d28-23ae-4835-99ab-fcb79a055137` |

---

## 4. Independent PayPal API Verification Evidence

### A. Orders v2 API Query
`GET https://api-m.sandbox.paypal.com/v2/checkout/orders/8RC0962473983884J`  
**HTTP Status**: `200 OK`

```json
{
  "id": "8RC0962473983884J",
  "status": "COMPLETED",
  "intent": "CAPTURE",
  "payer": {
    "name": {
      "given_name": "John",
      "surname": "Doe"
    },
    "email_address": "sb-yfhat53756342@personal.example.com",
    "payer_id": "CVQR3UNVUZA7G",
    "address": {
      "country_code": "US"
    }
  },
  "purchase_units": [
    {
      "reference_id": "default",
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
        "email_address": "sb-fsux153719951@business.example.com",
        "merchant_id": "F4M6RDMBJ5FFA",
        "display_data": {
          "brand_name": "AgentPay Nexus"
        }
      },
      "payments": {
        "captures": [
          {
            "id": "20L952323A1910922",
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
                "value": "0.72"
              },
              "net_amount": {
                "currency_code": "USD",
                "value": "7.28"
              }
            },
            "create_time": "2026-11-06T16:27:37Z",
            "update_time": "2026-11-06T16:27:37Z"
          }
        ]
      }
    }
  ]
}
```

### B. Payments Captures API Query
`GET https://api-m.sandbox.paypal.com/v2/payments/captures/20L952323A1910922`  
**HTTP Status**: `200 OK`

```json
{
  "id": "20L952323A1910922",
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
      "value": "0.72"
    },
    "net_amount": {
      "currency_code": "USD",
      "value": "7.28"
    }
  },
  "create_time": "2026-11-06T16:27:37Z",
  "update_time": "2026-11-06T16:27:37Z"
}
```

---

## 5. Independent Supabase PostgreSQL Verification Evidence

**Host Database**: Supabase Hosted PostgreSQL 17.11 (`aynszmhshjcuiywnooll`)  
**Table**: `transactions` & `tasks`

```sql
SELECT id, user_id, task_id, paypal_order_id, paypal_capture_id, amount, currency, payment_status, provider, updated_at
FROM transactions
WHERE paypal_order_id = '8RC0962473983884J';
```

**Retrieved Record**:
- **Transaction ID**: `9aa62d28-23ae-4835-99ab-fcb79a055137`
- **User ID**: `user_guest_01`
- **Task ID**: `f615a14d-0317-4018-885c-1a89e8565431`
- **PayPal Order ID**: `8RC0962473983884J`
- **PayPal Capture ID**: `20L952323A1910922`
- **Amount**: `8.0`
- **Currency**: `USD`
- **Payment Status**: `completed`
- **Provider**: `paypal_sandbox`
- **Created At**: `2026-11-06 15:24:49 UTC`
- **Updated At**: `2026-11-06 16:27:38 UTC`

---

## 6. Task Completion & Deliverable Unlock Verification

- **Task Status**: `completed`
- **Budget**: `$10.00 USD`
- **Total Cost**: `$8.00 USD`
- **Final Deliverable**: Unlocked (10,143 bytes of cross-border payment evaluation and research).
- **Subtask Graph**: 8 / 8 nodes resolved successfully:
  1. `planning` (`agent_orchestrator_00`) — COMPLETED
  2. `research` (`agent_research_01`) — COMPLETED
  3. `data_analysis` (`agent_analysis_02`) — COMPLETED
  4. `content_generation` (`agent_content_03`) — COMPLETED
  5. `quality_assurance` (`agent_qa_04`) — COMPLETED
  6. `finance_calculation` (`agent_finance_05`) — COMPLETED
  7. `payment_approval` (`agent_payment_06`) — COMPLETED
  8. `final_delivery` (`agent_orchestrator_00`) — COMPLETED

---

## 7. Key Findings & Cross-Border Insights

1. **Inbound Cross-Border USD Capability**: A US Personal Sandbox buyer can successfully authorize and settle a USD-denominated order with an Indian Business Sandbox merchant, confirming that inbound cross-border settlement functions cleanly in the PayPal Sandbox environment.
2. **Fee Structure**: PayPal applied a processing fee of `$0.72 USD` on the $8.00 transaction, resulting in a net receivable of `$7.28 USD` to the Indian Business merchant account.
3. **End-to-End Execution Flow**: The transaction executed seamlessly through the production web UI: the buyer authorized the order on PayPal Sandbox, was returned to the application callback URL with `?approved=true&token=8RC0962473983884J`, the backend pre-verified the `APPROVED` status, captured the funds, updated the database, and unlocked all deliverables.

**Final Result**: **PASSED**
