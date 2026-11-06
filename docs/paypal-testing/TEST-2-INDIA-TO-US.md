# Test 2 Evidence — Cross-Border Indian Personal Buyer to US Business Seller

**Test Status**: **PASSED (Twice Verified: Run 2A & Run 2B)**  
**Production URL**: [https://agentpay-nexus.vercel.app](https://agentpay-nexus.vercel.app)  
**Deployment Commit**: `34167b0` on `main`  
**Deployment ID**: `dpl_Bsu1vZCrwuAoqpDRcqbxD8EiQq8j`  
**Database**: Supabase Hosted PostgreSQL 17.11 (`aynszmhshjcuiywnooll`)  

---

## 1. Test Objective & Cross-Border Scope

Determine whether an Indian Personal Sandbox buyer can successfully purchase an autonomous multi-agent task execution from the US Business Sandbox merchant using a USD-denominated PayPal Orders v2 order.

This tested cross-border transaction dynamics across two independent runs:
- **Run 2A**: Automated multi-agent orchestration execution.
- **Run 2B**: Independent manual Auto Run executed by the user with Visa card funding.

Key verification points:
- Acceptance of USD orders by Indian Personal buyers in PayPal Sandbox.
- Automatic international cross-border fee assessment by PayPal ($0.89 USD fee on $8.00 gross vs. $0.77 for domestic US).
- Automatic server-side status verification (`APPROVED` &rarr; `COMPLETED`) and unlock of autonomous multi-agent deliverables upon return to the production application.

---

## 2. Participant Accounts & Shared Configuration

| Role | Property | Value |
| :--- | :--- | :--- |
| **Buyer** | Account Type | Personal Sandbox Account |
| **Buyer** | Registered Country | `IN` (India) |
| **Buyer** | Payer Account | `sb-dp8mz53751118@personal.example.com` (Payer ID: `ZAMAQ996PTJ6N`) |
| **Buyer** | Funding Source | Indian Personal Sandbox Account (INR balance & Visa Sandbox card) |
| **Seller / Merchant** | Account Type | Business Sandbox Account (`sb-jffuj53655931@business.example.com`) |
| **Seller / Merchant** | Merchant ID | `U6DA8TWKPA2HQ` |
| **Seller / Merchant** | Registered Country | `US` (United States) |
| **Payment Protocol** | API Standard | PayPal REST API v2 (Orders v2 & Payments Captures v2) |
| **Environment** | Operating Mode | `sandbox` (`https://api-m.sandbox.paypal.com`) |
| **Transaction Currency** | Order Currency | `USD` |

---

## 3. Execution Run 2A — Automated Multi-Agent Pipeline Run

**Run Type**: Automated Antigravity Multi-Agent Workflow Execution  
**Timestamp**: 2026-11-06 14:58:50 UTC (20:28:50 IST)  
**Task ID**: `e2a619e7-7d06-4061-bce0-9ec7e5dbb629`  
**Task Title**: India EV Market Research & Strategy  
**Task Budget**: `$10.00 USD`  
**PayPal Order ID**: `3NU881071F2178519`  
**PayPal Capture ID**: `4XF639955L031754T`  
**Gross Order Amount**: `$8.00 USD`  
**PayPal Fee**: `$0.89 USD` (International cross-border fee)  
**Net Amount to Seller**: `$7.11 USD`  
**Final Capture**: `true`  
**Seller Protection**: `ELIGIBLE` (`ITEM_NOT_RECEIVED`, `UNAUTHORIZED_TRANSACTION`)  
**Supabase Transaction ID**: `c65566e4-e354-4fe5-a471-a9c1185751be`  
**Task Status**: `completed` (8/8 nodes resolved, 10,949 bytes deliverable unlocked)  

### Independent API Evidence (Run 2A)

`GET https://api-m.sandbox.paypal.com/v2/checkout/orders/3NU881071F2178519` &rarr; `HTTP 200 OK`
```json
{
  "id": "3NU881071F2178519",
  "status": "COMPLETED",
  "intent": "CAPTURE",
  "amount": { "currency_code": "USD", "value": "8.00" },
  "payee": { "email_address": "sb-jffuj53655931@business.example.com", "merchant_id": "U6DA8TWKPA2HQ" },
  "payments": {
    "captures": [
      {
        "id": "4XF639955L031754T",
        "status": "COMPLETED",
        "amount": { "currency_code": "USD", "value": "8.00" },
        "seller_receivable_breakdown": {
          "gross_amount": { "currency_code": "USD", "value": "8.00" },
          "paypal_fee": { "currency_code": "USD", "value": "0.89" },
          "net_amount": { "currency_code": "USD", "value": "7.11" }
        }
      }
    ]
  }
}
```

---

## 4. Execution Run 2B — Independent Manual Auto Run (Visa Funding)

**Run Type**: Manual Auto Run via Production Dashboard with Visa Card  
**Timestamp**: 2026-11-06 15:00:07 UTC (20:30:07 IST)  
**Task ID**: `37543f0d-e9da-4fe7-aa59-8ed6629e92b3`  
**Task Title**: Electric Vehicle Market Research Report India  
**Task Budget**: `$10.00 USD`  
**PayPal Order ID**: `8MU87667XB022832A`  
**PayPal Capture ID**: `0RE44251J5276325P`  
**Official PayPal Order Amount**: `$8.00 USD`  
**User-Reported Card Billing**: `₹782 INR` *(User-reported Visa credit card billing statement figure; distinct from the PayPal-settled $8.00 USD order amount)*  
**PayPal Fee**: `$0.89 USD` (International cross-border fee)  
**Net Amount to Seller**: `$7.11 USD`  
**Final Capture**: `true`  
**Seller Protection**: `ELIGIBLE` (`ITEM_NOT_RECEIVED`, `UNAUTHORIZED_TRANSACTION`)  
**Supabase Transaction ID**: `fa743cd4-3a96-4583-a270-bfc509165e28`  
**Task Status**: `completed` (8/8 nodes resolved, 9,721 bytes deliverable unlocked)  

### Independent API Evidence (Run 2B)

`GET https://api-m.sandbox.paypal.com/v2/checkout/orders/8MU87667XB022832A` &rarr; `HTTP 200 OK`
```json
{
  "id": "8MU87667XB022832A",
  "status": "COMPLETED",
  "intent": "CAPTURE",
  "payer": {
    "name": { "given_name": "John", "surname": "Doe" },
    "email_address": "sb-dp8mz53751118@personal.example.com",
    "payer_id": "ZAMAQ996PTJ6N",
    "address": { "country_code": "IN" }
  },
  "purchase_units": [
    {
      "amount": { "currency_code": "USD", "value": "8.00" },
      "payee": {
        "email_address": "sb-jffuj53655931@business.example.com",
        "merchant_id": "U6DA8TWKPA2HQ"
      },
      "payments": {
        "captures": [
          {
            "id": "0RE44251J5276325P",
            "status": "COMPLETED",
            "amount": { "currency_code": "USD", "value": "8.00" },
            "seller_receivable_breakdown": {
              "gross_amount": { "currency_code": "USD", "value": "8.00" },
              "paypal_fee": { "currency_code": "USD", "value": "0.89" },
              "net_amount": { "currency_code": "USD", "value": "7.11" }
            },
            "create_time": "2026-11-06T15:00:07Z",
            "update_time": "2026-11-06T15:00:07Z"
          }
        ]
      }
    }
  ]
}
```

### Payments Captures API Evidence (Run 2B)

`GET https://api-m.sandbox.paypal.com/v2/payments/captures/0RE44251J5276325P` &rarr; `HTTP 200 OK`
```json
{
  "id": "0RE44251J5276325P",
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
    "gross_amount": { "currency_code": "USD", "value": "8.00" },
    "paypal_fee": { "currency_code": "USD", "value": "0.89" },
    "net_amount": { "currency_code": "USD", "value": "7.11" }
  },
  "create_time": "2026-11-06T15:00:07Z",
  "update_time": "2026-11-06T15:00:07Z"
}
```

### Supabase Database Evidence (Run 2B)

```sql
SELECT id, user_id, task_id, paypal_order_id, paypal_capture_id, amount, currency, payment_status, provider, updated_at
FROM transactions
WHERE paypal_order_id = '8MU87667XB022832A';
```

- **Transaction ID**: `fa743cd4-3a96-4583-a270-bfc509165e28`
- **User ID**: `user_guest_01`
- **Task ID**: `37543f0d-e9da-4fe7-aa59-8ed6629e92b3`
- **PayPal Order ID**: `8MU87667XB022832A`
- **PayPal Capture ID**: `0RE44251J5276325P`
- **Amount**: `8.0 USD`
- **Payment Status**: `completed`
- **Provider**: `paypal_sandbox`
- **Created At**: `2026-11-06 14:59:46 UTC`
- **Updated At**: `2026-11-06 15:00:07 UTC`
- **Subtask Graph**: 8 / 8 nodes resolved (`planning`, `research`, `data_analysis`, `content_generation`, `quality_assurance`, `finance_calculation`, `payment_approval`, `final_delivery`)
- **Deliverable**: Unlocked (9,721 bytes)

---

## 5. Comparative Run Analysis & Summary

| Parameter | Run 2A (Automated Run) | Run 2B (Manual Auto Run) |
| :--- | :--- | :--- |
| **Execution Method** | Background API Pipeline Advance | Production Web UI Auto Run |
| **Buyer Account** | Indian Personal (`IN`) | Indian Personal (`IN`, `sb-dp8mz53751118@personal.example.com`) |
| **Funding Mechanism** | PayPal Sandbox Balance | PayPal Sandbox Visa Card |
| **Settled Amount (PayPal)** | `$8.00 USD` | `$8.00 USD` |
| **User Card Billing (Reported)** | Direct USD | `₹782 INR` *(user-reported card billing)* |
| **PayPal Fee** | `$0.89 USD` (11.125%) | `$0.89 USD` (11.125%) |
| **Net to Seller** | `$7.11 USD` | `$7.11 USD` |
| **Task ID** | `e2a619e7-7d06-4061-bce0-9ec7e5dbb629` | `37543f0d-e9da-4fe7-aa59-8ed6629e92b3` |
| **Order ID** | `3NU881071F2178519` | `8MU87667XB022832A` |
| **Capture ID** | `4XF639955L031754T` | `0RE44251J5276325P` |
| **Status** | **PASSED** | **PASSED** |

**Final Result**: **PASSED (2x verified)**
