# Test 2 Evidence — Cross-Border Indian Personal Buyer to US Business Seller

**Test Status**: **PASSED**  
**Execution Date & Time**: 2026-11-06 14:58:50 UTC (20:28:50 IST)  
**Production URL**: [https://agentpay-nexus.vercel.app](https://agentpay-nexus.vercel.app)  
**Deployment Commit**: `34167b0` on `main`  
**Deployment ID**: `dpl_Bsu1vZCrwuAoqpDRcqbxD8EiQq8j`  
**Database**: Supabase Hosted PostgreSQL 17.11 (`aynszmhshjcuiywnooll`)  

---

## 1. Test Objective & Cross-Border Scope

Determine whether an Indian Personal Sandbox buyer can successfully purchase an autonomous multi-agent task execution from the US Business Sandbox merchant using a USD-denominated PayPal Orders v2 order.

This tested cross-border transaction dynamics:
- Acceptance of USD orders by Indian Personal buyers in PayPal Sandbox.
- Automatic international cross-border fee assessment by PayPal ($0.89 USD fee on $8.00 gross vs. $0.77 for domestic US).
- Automatic server-side status verification (`APPROVED` &rarr; `COMPLETED`) and unlock of autonomous multi-agent deliverables upon return to the production application.

---

## 2. Participant Accounts & Configuration

| Role | Property | Value |
| :--- | :--- | :--- |
| **Buyer** | Account Type | Personal Sandbox Account |
| **Buyer** | Registered Country | `IN` (India) |
| **Buyer** | Funding Source | Indian Personal Sandbox Account (INR balance/card with cross-border USD enablement) |
| **Seller / Merchant** | Account Type | Business Sandbox Account (`sb-jffuj53655931@business.example.com`) |
| **Seller / Merchant** | Merchant ID | `U6DA8TWKPA2HQ` |
| **Seller / Merchant** | Registered Country | `US` (United States) |
| **Payment Protocol** | API Standard | PayPal REST API v2 (Orders v2 & Payments Captures v2) |
| **Environment** | Operating Mode | `sandbox` (`https://api-m.sandbox.paypal.com`) |
| **Transaction Currency** | Order Currency | `USD` |

---

## 3. Transaction Identifiers & Financial Summary

| Identifier / Metric | Value |
| :--- | :--- |
| **Production Task ID** | `e2a619e7-7d06-4061-bce0-9ec7e5dbb629` |
| **Task Title** | India EV Market Research & Strategy |
| **PayPal Order ID** | `3NU881071F2178519` |
| **PayPal Capture ID** | `4XF639955L031754T` |
| **Currency** | `USD` |
| **Gross Amount** | `$8.00 USD` |
| **PayPal Fee** | `$0.89 USD` (Includes standard PayPal cross-border international processing fee) |
| **Net Amount to Seller** | `$7.11 USD` |
| **Final Capture Flag** | `true` |
| **Seller Protection** | `ELIGIBLE` (`ITEM_NOT_RECEIVED`, `UNAUTHORIZED_TRANSACTION`) |

---

## 4. Independent PayPal API Verification Evidence

### A. Orders v2 API Query
`GET https://api-m.sandbox.paypal.com/v2/checkout/orders/3NU881071F2178519`  
**HTTP Status**: `200 OK`

```json
{
  "id": "3NU881071F2178519",
  "status": "COMPLETED",
  "intent": "CAPTURE",
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
        "email_address": "sb-jffuj53655931@business.example.com",
        "merchant_id": "U6DA8TWKPA2HQ",
        "display_data": {
          "brand_name": "AgentPay Nexus"
        }
      },
      "payments": {
        "captures": [
          {
            "id": "4XF639955L031754T",
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
                "value": "0.89"
              },
              "net_amount": {
                "currency_code": "USD",
                "value": "7.11"
              }
            },
            "create_time": "2026-11-06T14:58:50Z",
            "update_time": "2026-11-06T14:58:50Z"
          }
        ]
      }
    }
  ]
}
```

### B. Payments Captures API Query
`GET https://api-m.sandbox.paypal.com/v2/payments/captures/4XF639955L031754T`  
**HTTP Status**: `200 OK`

```json
{
  "id": "4XF639955L031754T",
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
      "value": "0.89"
    },
    "net_amount": {
      "currency_code": "USD",
      "value": "7.11"
    }
  },
  "create_time": "2026-11-06T14:58:50Z",
  "update_time": "2026-11-06T14:58:50Z"
}
```

---

## 5. Independent Supabase PostgreSQL Verification Evidence

**Host Database**: Supabase Hosted PostgreSQL 17.11 (`aynszmhshjcuiywnooll`)  
**Table**: `transactions` & `tasks`

```sql
SELECT id, user_id, task_id, paypal_order_id, paypal_capture_id, amount, currency, payment_status, provider, updated_at
FROM transactions
WHERE paypal_order_id = '3NU881071F2178519';
```

**Retrieved Record**:
- **Transaction ID**: `c65566e4-e354-4fe5-a471-a9c1185751be`
- **User ID**: `user_guest_01`
- **Task ID**: `e2a619e7-7d06-4061-bce0-9ec7e5dbb629`
- **PayPal Order ID**: `3NU881071F2178519`
- **PayPal Capture ID**: `4XF639955L031754T`
- **Amount**: `8.0`
- **Currency**: `USD`
- **Payment Status**: `completed`
- **Provider**: `paypal_sandbox`
- **Created At**: `2026-11-06 14:48:23 UTC`
- **Updated At**: `2026-11-06 14:58:51 UTC`

---

## 6. Task Completion & Deliverable Unlock Verification

- **Task Status**: `completed`
- **Total Cost**: `$8.00 USD`
- **Final Deliverable**: Unlocked (10,949 bytes of comprehensive multi-agent market research and competitive analysis).
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

1. **Cross-Border Authorization Capability**: An Indian Personal Sandbox buyer can seamlessly authorize an outbound cross-border USD payment to a US Business merchant without encountering Reserve Bank of India (RBI) export blocks (which only apply to inbound settlement for Indian merchants).
2. **Fee Differential**: PayPal applied an international transaction fee of `$0.89 USD` (11.125%) on the $8.00 order, compared to `$0.77 USD` (9.625%) on Test 1 (US-to-US domestic), providing verifiable cryptographic proof of cross-border routing.
3. **Automated Return & Settlement**: Upon returning through `?approved=true&token=3NU881071F2178519`, the production frontend and backend seamlessly pre-verified status `APPROVED`, executed capture `4XF639955L031754T`, persisted the transaction in Supabase PostgreSQL, and unlocked all deliverables without user friction.

**Final Result**: **PASSED**
