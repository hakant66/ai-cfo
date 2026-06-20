# BUSINESS.MD: AI CFO Financial Platform for Retail Sellers

**Intended Audience**: CFOs, Finance Directors, Controllers of retail companies with multi-channel commerce (Shopify, direct sales, marketplace).

**Document Purpose**: Explain the financial capabilities, payment orchestration, and business value of AI CFO.

---

## Executive Summary

AI CFO is a **financial intelligence and payment reconciliation platform** that gives retail CFOs visibility into cash flow, revenue profitability, and operational finance in **one unified dashboard**. It integrates payment processors (Stripe), bank accounts (Wise/TransferWise), and operational data (Shopify, inventory) to answer CFO questions in seconds instead of hours.

### Three Core Problems It Solves

1. **Cash Visibility Across Channels**
   - Problem: Sales come in via Stripe (online), direct bank transfers, marketplace payouts. Where is the money really?
   - Solution: AI CFO aggregates all account balances (Wise, bank) and shows which ones have what in seconds.

2. **True Profitability After Fees**
   - Problem: Stripe shows gross revenue, but the actual amount to the bank is lower due to fees. P&L is mysterious.
   - Solution: Stripe True Net Margin shows gross → fees → net with breakdowns by transaction type.

3. **Multi-Currency Complexity**
   - Problem: Wise transfers involve exchange rates. Stripe charges in multiple currencies. Reports are a mess.
   - Solution: FX tracking, exchange rate snapshots, currency-aware reporting, automatic rate updates.

---

## 🏦 Wise Integration: Multi-Currency Bank Account Management

**What is Wise?** Wise (formerly TransferWise) is a bank-connected account service with great FX rates. Retail sellers use it to hold inventory in multiple currencies, receive international payments, and move money between regions affordably.

### Why Wise Integration Matters

**Without integration:**
- Login to Wise dashboard separately
- Copy/paste balances into Excel
- Manually calculate FX impact
- Can't correlate Wise transfers with bank deposits
- No automatic alerts when balance drops

**With AI CFO:**
- Balances update automatically (via webhooks)
- Wise balances show **in company currency** for easy comparison
- See all currencies side-by-side on the Morning Brief
- Ask "Did the GBP transfer arrive?" and get instant answers
- Catch cash flow issues before they happen

### How Wise Connection Works

**OAuth Flow (Secure & Modern)**
1. User clicks "Connect Wise" in Admin panel
2. Redirected to Wise login page (user stays in control)
3. User approves specific permissions (read-only by default)
4. AI CFO receives encrypted token (never sees password)
5. Token refreshes automatically; no manual key rotation

**What Data AI CFO Pulls**
| Data | Frequency | Use Case |
|------|-----------|----------|
| Balance accounts | On-demand | "How much GBP do we have?" |
| Current balances | Real-time (webhooks) | Morning brief |
| Transaction history | Daily sync | Reconcile transfers, track cash flows |
| Account details | On-demand | Know which account is which |
| Exchange rates | Daily | Apply FX rates to multi-currency sales |

**Data Security**
- Tokens encrypted at rest using RSA-2048 keys
- Keys managed separately from database
- OAuth tokens auto-refresh before expiration
- Webhook signatures validated on every update
- Audit logs track all Wise data access

### Use Cases

**Daily Cash Management**
```
Morning Brief shows:
- Total cash position: $487,340 (all accounts combined)
  - Bank account: $250,000 USD
  - Wise GBP: £18,000 (≈ $22,680 @ cached rate)
  - Wise EUR: €45,000 (≈ $48,600 @ cached rate)
  - Wise JPY: ¥6,500,000 (≈ $44,000 @ cached rate)
  - Stripe payout pending: $122,060 (arrives tomorrow)

CFO quick check: "We're okay for payroll and inventory buy tomorrow."
```

**Monthly Reconciliation**
```
Ask CFO: "Show me all Wise transfers in June."
Result: 
- Transfer to supplier in UK: £8,000 (2-day settlement)
- Transfer to India office: ₹500,000 (same day)
- Internal: €45,000 from London account (instant)

Match against bank statement: ✓ All cleared.
```

**FX Risk Management**
```
Exchange Rates page shows:
- GBP/USD: 1.27 (avg last 30 days)
- EUR/USD: 1.08 (avg last 30 days)

Finance team manually sets floor rates for budgeting:
- GBP/USD: 1.20 (conservative)
- EUR/USD: 1.00 (conservative)

AI CFO uses manual rates for cash forecast (not optimistic rates).
```

**Payment Timing & Cash Forecast**
```
7-day cash forecast shows:
- Today: $487k in accounts
- Tomorrow: +$122k (Stripe payout arrives)
- Day 4: -$80k (supplier payment due)
- Day 5: -$45k (payroll)
- Day 7: +$250k (expected Shopify sales processed)

Projected minimum: $332k (Day 4). Safe.
```

---

## 💳 Stripe Integration: Payment Processing & True Net Margin

**What is Stripe?** Stripe is the #1 online payment processor. Every Shopify sale, direct payment, and marketplace order typically flows through Stripe. Stripe also offers Connect for marketplace payments.

### Why Stripe Integration Matters

**The Stripe Problem:**
- Shopify shows "Revenue: $50,000 today"
- Stripe shows "Gross charges: $50,000"
- **But your bank shows: $48,250** (after 3.2% + $0.30 per transaction)
- **Where did $1,750 go?** Stripe fees. Were they worth it? How much per channel?

**What AI CFO Adds:**
- **True Net Margin** breaks down every transaction: gross → fee → net
- Track fees by **type** (payment fee, refund, chargeback, FX fee)
- See **actual cash** that hits your bank daily
- Compare channels: which ones are most profitable after fees?
- Identify **fee trends**: are fees increasing? Should we negotiate volume discounts?

### Stripe True Net Margin Explained

Every payment processed by Stripe generates a **balance transaction**. AI CFO enriches it with:

```
Transaction Detail (Stripe):
  Charge: $100.00 USD
  Stripe fee: -$3.20 (2.9% + $0.30)
  Net deposit: $96.80
  
AI CFO enriches with:
  Transaction type: "charge" (could also be refund, payout, chargeback, etc.)
  Payment method: Credit card
  Customer: repeat_customer (via metadata)
  Margin %: 96.8% (of gross)
  Currency: USD
  Timestamp: 2026-06-20 14:32:45 UTC
  
Optional: Tax breakdown (from invoice metadata)
```

### Using True Net Margin for Business Decisions

**Daily Monitoring**
```
Sales Quality page → True Net Margin (Stripe)

Yesterday: 247 charges
  Gross: $12,840
  Fees: -$389
  Net: $12,451
  Margin %: 96.9%
  
By payment method:
  Credit card: $10,200 gross, 3.0% fee average
  Debit card: $1,840 gross, 2.4% fee average
  ACH: $800 gross, 0.1% fee average
  
Insight: Debit cards cost less. Market them more?
```

**Weekly Channel Comparison**
```
Ask CFO: "Compare Shopify vs. direct payment margin."

Shopify channel:
  Volume: 1,250 orders
  Gross: $62,500
  Stripe fees: $1,975 (3.16%)
  Net: $60,525
  
Direct web payments:
  Volume: 180 orders
  Gross: $18,000
  Stripe fees: $450 (2.5%)
  Net: $17,550
  
Insight: Direct channel has lower fees. Higher AOV too. Worth more marketing budget.
```

**Monthly Reconciliation Against P&L**
```
Stripe revenue sync pulls:
- All balance transactions (last 30 days)
- All charges with expanded balance transaction data
- All refunds with balance transaction links

Reconcile against accounting:
  Stripe net deposits: $487,320
  Bank deposits received: $487,320 ✓
  Days to settlement: 2-3 business days (track payout schedule)
```

**Cash Flow Timing**
```
Stripe Payouts page shows:
- Payout #1: $125,000 (arrives 2026-06-22)
- Payout #2: $98,500 (arrives 2026-06-23)
- Payout #3: $65,200 (scheduled for 2026-06-24)

AI CFO uses these in 7/14/30-day cash forecast.
CFO knows exactly when liquidity arrives, can plan payroll.
```

### Stripe Integration Architecture

**How It Works**
```
Frontend (Sales Quality page)
  ↓
Backend API: POST /connectors/stripe/metrics/true-net-margin
  ↓
stripe-api service (calls Stripe SDK)
  ↓
Stripe API (BalanceTransaction.list, Charge.retrieve, Customer.retrieve)
  ↓
Response: Array of { gross, fee, net, margin_pct, customer_metadata, ... }
  ↓
Frontend displays: KPI tiles, margin %, fee trends
```

**Real-Time Updates (Webhooks)**
```
When a new charge, refund, or payout occurs:
  1. Stripe sends webhook to AI CFO backend
  2. Backend validates signature (security)
  3. Backend stores event ID (deduplication)
  4. Backend enqueues Celery job: refresh True Net Margin for last 3 days
  5. User sees updated metrics on refresh (not instant, but < 5 min)
```

**Supported Payment Types in Revenue Sync**
- **Charges**: Payment from customer → net after Stripe fee
- **Refunds**: Returned charge → negative net
- **Balance transactions**: Fees, chargebacks, disputes, transfers
- **Connect transfers**: If using Stripe Connect for marketplace
- **Tax**: Embedded in invoice metadata

### Stripe Best Practices Implemented

✅ **Least privilege**: Restricted API keys (can only list/retrieve, not create)
✅ **Webhook validation**: Stripe-Signature verified with HMAC
✅ **Idempotent processing**: Events de-duped by Stripe event ID
✅ **Date windows**: Configurable sync windows (default 30 days for revenue)
✅ **Error handling**: Timeouts, retries, detailed error messages
✅ **Multi-account**: Supports Stripe Connect connected accounts
✅ **Currency aware**: Handles FX in balance transactions and charges
✅ **Audit trail**: All syncs logged with user, timestamp, row count

---

## 📊 Morning Brief: Daily Financial Snapshot

The Morning Brief is the **first page a CFO checks**. It shows the financial state right now, in under 5 seconds.

### What You See

**Current cash position** (aggregated across all accounts)
```
Total: $487,340
  Bank: $250,000
  Wise: $237,340 (multi-currency converted)
Sources: Bank deposits, Wise balances (last updated 2 min ago)
Confidence: High (all accounts connected)
```

**Yesterday's performance**
```
Net Sales: $12,840
Cost of Goods Sold: -$5,120
Refunds: -$180
Discounts: -$640
Ad Spend: -$2,500
Other Expenses: -$800

Gross Margin: 60.2% (sales - COGS / sales)
Contribution Margin: 45.1% (sales - COGS - ads / sales)
```

**Cash forecasts** (when will we run out of money?)
```
7-day outlook: +$45,280 (expecting payouts, sales)
14-day outlook: +$120,560
30-day outlook: +$380,240

Minimum cash in next 7 days: $432,060 (after payables)
Status: Safe ✓
```

**Payables & commitments** (what's due?)
```
7-day: $80,000 (inventory purchase, rent)
Status: Have $487k, need $80k. Safe.

14-day: $125,000 (payroll, suppliers)
30-day: $280,000 (including seasonal adjustments)
```

**Alerts & flags** (things to watch)
```
⚠️ Inventory low: Widget SKU below 100 units (reorder ASAP)
⚠️ Customer concentration: Top 5 customers = 35% of sales
✅ No unusual refund spike
✅ All payments processed on time
```

### Why Morning Brief Matters

**Time saved**: One-click overview instead of logging into 5 different systems.
**Confidence**: Metrics include data completeness scores. Know when numbers are stale.
**Decision speed**: See an alert? Ask CFO for context. ("Why is cash forecast down?")
**Audit trail**: Every metric shows last refresh time and data sources.

---

## 📈 Sales Quality: Channel & Customer Analytics

Retail sellers face a strategic question: **Are we selling to the right customers, in the right channels?**

Sales Quality answers this with analytics on:

### KPIs Dashboard
```
Net Sales: $487,320 (last 30 days)
  Confidence: High
  Breakdown: Shopify $380k, Direct $107k

Average Order Value (AOV): $156.25
  By channel:
    Shopify: $145.30
    Direct web: $189.20 (higher value, fewer orders)
    Insight: Direct channel more profitable?

Units Per Order: 1.8
  Suggests bundling? Cross-selling opportunity?
```

### Channel Mix
```
Shopify: 65% of orders (but 78% of revenue)
  Insight: Shopify brings higher AOV
  
Direct web: 35% of orders (22% of revenue)
  Insight: Smaller orders, but lower payment fees

Marketplace (if connected): [would show here]
```

### Customer Segmentation
```
New customers: 25% of orders, 18% of revenue
Repeat customers: 75% of orders, 82% of revenue
  Insight: Focus on retention, high LTV

Top customer: $87k (17.8% of revenue)
  Risk: Concentration. Diversify?
```

### Product Analysis
```
SKU concentration:
  Top 5 products: 48% of revenue
  Long tail (50+ SKUs): 52% of revenue
  Insight: Balanced. Not over-reliant on one product.

By category:
  Electronics: 35% ($170k)
  Apparel: 45% ($219k) ← Most profitable
  Home: 20% ($97k)
```

### Geographic Distribution
```
Sales by region:
  US: 70%
  Canada: 12%
  UK: 8%
  Other: 10%
  
Currency impact:
  USD sales: $340k
  CAD sales: $58k (paid Wise 1.24 rate, avg was 1.27 → -$23 FX loss)
  GBP sales: $39k (paid 1.27 rate, avg was 1.28 → +$310 FX gain)
```

### True Net Margin (Stripe)
```
Gross revenue: $487,320
Stripe fees: -$15,520 (3.2% average)
Net revenue: $471,800
Margin %: 96.8%

Trend (30 days):
  Week 1: 96.5%
  Week 2: 96.8%
  Week 3: 97.1%
  Week 4: 96.9%
  
Insight: Fees stable. No unusual activity.
```

### Why This Matters for CFO

**Strategic pricing**: Which channels/products are most profitable after fees? Allocate marketing budget accordingly.

**Cash flow timing**: Understand which customers pay fast (credit card) vs. slow (invoice terms).

**Concentration risk**: "Top 5 customers = 48% of revenue" is a vulnerability. One churns = 48% revenue drop.

**FX impact**: Multi-currency sales have hidden FX costs. Track them separately.

---

## 🔧 Operations Finance: Payables, Inventory, Exchange Rates

Beyond revenue, CFOs need operational visibility.

### Payables Tracking

**Bill Due Dates**
```
Due in 7 days:
  - Supplier invoice #2847: $35,000 (inventory)
  - Rent payment: $15,000
  - Utilities: $2,000
  Total due: $52,000

Due in 14-30 days:
  - Supplier invoice #2851: $28,000
  - Payroll: $45,000
  Total due: $73,000

Action: Have $487k cash. Safe. But prioritize cash-on-hand for Q3 inventory buy.
```

**Criticality & Negotiation**
```
High priority (stop operations if unpaid):
  - Supplier (inventory): Payment terms net 30 (negotiate to net 45?)
  - Payroll: Must pay on time
  - Rent: Contractual obligation

Medium priority:
  - Professional services: Can stretch a few days
  - Marketing vendors: Monthly invoices, flexible

Insight: Ask suppliers if they offer 2% discount for early payment.
If we pay in 10 days instead of 30, we get 2% × $35k = $700 discount.
Cost of capital to pay early? ~1% per 20 days. Worth it!
```

### Inventory Health

**Stock Levels**
```
Widget Pro (high volume):
  Current: 850 units
  Reorder level: 500
  Status: ✓ Safe

Gadget Basic (seasonal):
  Current: 45 units
  Reorder level: 200
  Status: ⚠️ LOW - reorder ASAP (15-day lead time from supplier)

Deluxe Bundle (low volume):
  Current: 2,340 units
  Reorder level: 100
  Status: ⚠️ OVERSTOCK - ties up $145k in capital

Action: 
  - Immediate reorder for Gadget Basic
  - Run clearance sale for Deluxe Bundle
  - Free up $145k for payables/new inventory
```

### Exchange Rates

**Daily Tracking**
```
GBP/USD:
  Current: 1.2730
  30-day avg: 1.2650
  30-day min: 1.2580
  30-day max: 1.2890
  
Manual override (set by Finance):
  Conservative rate: 1.2500
  Budget rate: 1.2400
  
Impact: 
  UK sales of £100k valued at:
    Current: $127,300
    Conservative: $125,000 (-$2,300)
    Budget: $124,000 (-$3,300)
```

**Use Cases**
- **Budgeting**: Use conservative rates, not optimistic ones
- **Reforecasting**: Track actual rates vs. budgeted. Variance analysis.
- **Cost comparison**: Is it cheaper to buy inventory in USD or GBP at current rates?
- **Payment timing**: "Should we pay GBP supplier now or wait 2 weeks?" (check rate forecast)

---

## 🤖 Ask CFO: AI-Powered Financial Assistant

Beyond dashboards, CFOs need to ask ad-hoc questions. "Ask CFO" is a chatbot that understands financial context.

### Natural Language Queries

**Cash flow questions**
```
User: "Do we have enough cash for the India office expansion ($250k)?"
Ask CFO: 
  Current cash: $487k
  30-day forecast minimum: $380k
  Available for expansion: $107k (after safety buffer)
  Recommendation: Not enough without a Stripe payout or Wise transfer first.
  
  Wait 2 days for Stripe payout ($122k)? Then we'd have $229k available.
  Or accelerate sales? 10% more sales in next week = +$50k.
```

**Inventory questions**
```
User: "Which SKUs should we mark down?"
Ask CFO:
  Current overstock:
    - Deluxe Bundle: 2,340 units, $145k tied up
    - Seasonal Item: 890 units, $67k tied up
  
  If we clear at 20% discount:
    Deluxe Bundle: Revenue +$29k, Cost -$58k margin loss
    Seasonal Item: Revenue +$13.4k, Cost -$26.8k margin loss
    
  But frees up $212k working capital for new inventory buy = net +$154k liquidity.
```

**Margin questions**
```
User: "Are subscription customers more profitable?"
Ask CFO:
  Subscription revenue (last 30 days): $145k
  Stripe fees (subscription): 2.1% = $3k
  Net: $142k
  
  One-time purchases: $342k
  Stripe fees: 3.2% = $11k
  Net: $331k
  
  Profitability per order:
    Subscription: $145k / 420 orders = $346/order
    One-time: $342k / 2,100 orders = $163/order
    
  Insight: Subscriptions are 2x more profitable. Invest in retention + expansion.
```

### Implementation

Ask CFO is built on **Dify**, an open-source LLM orchestration platform. AI CFO exposes tool endpoints (Morning Brief, Cash Forecast, Inventory Health, etc.) that Dify can call.

**Workflow**
```
User types: "How much cash will we have next week?"
  ↓
Dify chatflow receives input
  ↓
Dify decides to call tool: GET /tools/cash-forecast?days=7
  ↓
AI CFO backend computes forecast
  ↓
Dify receives structured data, generates natural language response
  ↓
User reads: "Based on current balances ($487k) and payables ($80k due in 7 days), 
             plus expected Stripe payout (+$122k), you'll have about $529k next week. Safe!"
```

### Data Sources

Ask CFO answers questions using:
- **Metrics**: Morning Brief, Cash Forecast, Sales Quality
- **Documents**: Uploaded P&Ls, contracts, invoices (searchable with AI embeddings)
- **Integrations**: Stripe True Net Margin, Wise transactions
- **Operational data**: Inventory snapshots, payables, exchange rates

---

## 🔐 Security & Compliance

CFO data is sensitive. AI CFO implements financial-grade security:

### Data Protection
- **Encryption at rest**: Wise OAuth tokens encrypted with RSA-2048
- **Encryption in transit**: TLS 1.3 for all API calls
- **Database security**: Company_id filtering on every query; no cross-company data leaks
- **Secret rotation**: API keys, webhook secrets, OAuth tokens regularly rotated

### Access Control
- **Role-based permissions**: Founder, Finance, Ops, Marketing, ReadOnly
- **Audit logs**: Every login, data access, settings change logged with user/timestamp
- **API key restrictions**: Stripe/Wise API keys limited to read-only or specific scopes
- **Webhook validation**: HMAC signatures verified on every incoming webhook

### Compliance Ready
- **PCI-DSS**: Stripe keys stored securely, never transmitted to frontend
- **GDPR**: Customer data in Stripe/Wise never duplicated unnecessarily
- **SOC 2**: Audit trails, data encryption, access controls in place
- **Multi-tenancy**: Perfect data isolation between companies

---

## 🚀 Getting Started

### Day 1: Basic Setup
1. Create company account
2. Connect Shopify (or manual inventory entry)
3. Set home currency and timezone
4. View Morning Brief (will show demo data if Shopify not connected)

### Day 2: Enable Payments
1. **Stripe setup**: Add secret key → enable True Net Margin metrics
2. **Wise setup**: Click "Connect Wise" → OAuth → balances auto-update
3. Check Sales Quality for Stripe fee breakdown
4. Verify cash position matches actual bank/Wise balances

### Day 3: Configure Operations
1. Add payables (supplier bills, payroll)
2. Set inventory reorder levels
3. Add exchange rate floor/ceiling for budgeting
4. Upload recent P&L and contracts for Ask CFO search

### Ongoing
1. Check Morning Brief each morning (2 minutes)
2. Ask CFO specific questions as they come up
3. Review Sales Quality weekly (customer/channel trends)
4. Update payables as bills come in
5. Adjust forecast parameters as business changes

---

## ROI & Business Impact

**Time savings**
- 15 min/day on cash position → manual spreadsheet
- 30 min/week on Stripe reconciliation → finance team
- 1 hr/week on FX tracking → multiple systems
= **~3 hours/week** saved per finance person

**Better decisions**
- Spot overstock before it becomes a $100k problem
- Negotiate Stripe volume discounts based on fee trends
- Move liquidity between Wise accounts optimally
- Identify concentration risk before customer churns
- Prioritize payables intelligently based on cash flow

**Risk reduction**
- Real-time alerts prevent cash shortfalls
- Webhook-driven updates catch payment issues immediately
- Audit trails support external audits
- Exchange rate tracking prevents FX surprises

---

## FAQ for CFOs

**Q: Does AI CFO replace my accountant?**
A: No. AI CFO is **forward-looking** (cash forecast, profitability) and **operational** (inventory, payables). Accountants do **historical** (GAAP P&L, tax reconciliation). AI CFO helps accountants work faster.

**Q: Can I trust the numbers?**
A: Every metric shows confidence score and data sources. If Shopify sync is old, confidence drops. You control when to use them.

**Q: How often do Wise/Stripe balances update?**
A: Every 2 minutes via webhooks. Manual sync available anytime. True Net Margin updates within 5 minutes of a transaction.

**Q: Can I export reports for the board?**
A: Yes. Sales Quality, Payables, Inventory all export to CSV. Ask CFO can summarize key findings.

**Q: What if I use different payment processors?**
A: Wise works with any bank. Stripe is pluggable. Easy to add PayPal, Square, Checkout.com, etc.

**Q: Is this GDPR compliant?**
A: Yes. Customer data is not duplicated; only transaction metadata used for analytics. Wise/Stripe are GDPR compliant; AI CFO inherits that.

**Q: Can I share access with my bookkeeper?**
A: Yes. Create users with Finance role. They can see/edit payables, upload documents, but can't change integrations.

---

## Support & Resources

- **Live Demo**: See dashboard with sample retail data
- **Documentation**: Technical & user guides for each feature
- **Training**: 1-on-1 onboarding session for finance teams
- **Stripe integration guide**: [docs/stripe-integration.md](docs/stripe-integration.md)
- **API reference**: Full REST API docs for developers
- **Support**: Email support@aicfo.dev or Slack community

---

**Last updated**: June 2026  
**Version**: 1.0.0
