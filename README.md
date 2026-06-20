# AI CFO - Financial Intelligence & Payment Orchestration Platform
Last updated: June 2026

AI CFO is a **CFO-grade financial intelligence system** designed for retail sellers with multi-channel commerce. It provides daily cash visibility, payment reconciliation, sales quality analytics, and intelligent financial decision-making through an AI-powered assistant.

## Core Features

### 📊 Morning Brief Dashboard
Unified daily cash position and financial snapshot:
- **Real-time cash position** (aggregated from all bank accounts and Wise profiles)
- **Yesterday's performance**: Net sales, COGS, refunds, discounts, ad spend
- **Margin metrics**: Gross margin, contribution margin
- **7/14/30-day cash forecasts** based on payables and revenue trends
- **Confidence scoring** based on data completeness
- **Integrated chatbot** (Ask CFO) for natural language financial queries

### 💳 Payment & Revenue Intelligence
- **Stripe integration** with True Net Margin metrics (gross → fees → net)
- **Revenue sync** (30-day default): aggregates balance transactions, charges, and refunds
- **Balance history & payouts**: Track cash flow patterns and payment timelines
- **Webhook-driven updates**: Real-time sync on new charges, refunds, and payouts

### 🏦 Multi-Currency Bank Account Management (Wise)
- **OAuth-secured connections** to Wise (TransferWise) business accounts
- **Multi-profile support**: Manage multiple profiles per environment (sandbox/production)
- **Real-time balances** across multiple currencies
- **Transaction history** with automatic categorization
- **Exchange rate snapshots** with manual override capability (Finance/Founder)
- **Webhook-driven incremental updates**: Keep balances fresh without full syncs

### 📈 Sales Quality Analytics
- **Channel mix & concentration**: Track sales by source and customer concentration
- **Order metrics**: Average order value (AOV), units per order (UPO), customer segmentation
- **SKU & category analysis**: Identify top-performing products and concentration risk
- **Geographic distribution**: Understand sales by region/country
- **Currency impact**: Track multi-currency sales with FX notes
- **True Net Margin** (Stripe): See actual profitability after all fees

### 📋 Operational Finance
- **Payables tracking**: Due dates, criticality levels, cash planning
- **Inventory health**: Monitor stock levels, risk flags for overstock/stockout
- **Exchange rates**: Live FX tracking with manual overrides
- **Document management**: Upload invoices, P&Ls, reports; searchable with AI embeddings

### 🤖 Ask CFO - AI Financial Assistant
Natural language financial queries with tool-calling:
- Morning brief snapshots
- Cash flow forecasts
- Inventory health checks
- Payables analysis
- Document search across uploaded financial records
- Integration with Dify for advanced LLM orchestration

## Business Requirements
- **CFO-grade decision system** with trusted metrics and audit trails
- **Multi-tenant safe** from day one (company_id scoped everywhere)
- **Role-based access** (Founder/Finance/Ops/Marketing/ReadOnly)
- **Daily CFO workflows** + real-time payment reconciliation
- **Secure integrations** with least-privilege access, encrypted tokens, and audit logs
- **Compliance-ready**: Data encryption, webhook validation, audit trails

## Problems Solved
- **Cash visibility gap**: Real-time position across all accounts and currencies
- **Revenue mystery**: Stripe fees and true profitability hidden in transaction details
- **Multi-currency complexity**: Exchange rates, Wise transfers, FX impact on margins
- **Payment timing**: When will cash actually hit the account? (Stripe payouts, transfers)
- **Inventory risk**: Overstock ties up cash; stockouts kill revenue
- **Payables planning**: When are bills due? Which ones impact cash flow most?
- **Sales quality drift**: Are we selling to the right customers? Channel concentration risk?
- **Financial knowledge silos**: CFO can't easily ask questions across data sources

## Technical Architecture Overview

AI CFO is a **multi-service application** designed for reliability and scalability:

### Services
- **Frontend (Next.js 14)**: React-based UI with real-time data fetching
- **Main Backend (FastAPI)**: REST APIs, auth, metrics, Dify integration
- **Stripe API Service (FastAPI)**: Dedicated microservice for Stripe SDK calls
- **Wise API Service (FastAPI)**: OAuth, webhooks, account management
- **Job Queue (Celery + Redis)**: Background sync jobs
- **Database (Postgres + pgvector)**: Relational data + document embeddings

### Data Flow
1. **User login** → JWT auth → company-scoped data access
2. **Dashboard load** → fetch Morning Brief metrics (cash, sales, payables)
3. **Stripe sync** → revenue, balance, payouts → True Net Margin metrics
4. **Wise sync** → OAuth → balance accounts → transactions & balances
5. **Webhooks** → Stripe/Wise events → incremental metric updates
6. **Ask CFO** → Dify chatflow → tool calls → metric/document responses

### Key Design Principles
- **Company isolation**: All queries filtered by `company_id`
- **Least privilege**: Integrations use restricted API keys and OAuth scopes
- **Audit trail**: All changes logged with user, timestamp, and action
- **Metric provenance**: Every number tracks its source and refresh time
- **Idempotent webhooks**: Stripe/Wise events de-duped by event ID
- **Encryption at rest**: Wise OAuth tokens encrypted with RSA keys

## Technical Stack
- Frontend: Next.js 14 (App Router), TypeScript, Tailwind, shadcn/ui, SWR, Zod
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic
- Stripe API: FastAPI (separate service, dedicated microservice for Stripe SDK)
- Wise API: FastAPI (separate service, OAuth + webhook management)
- Database: Postgres + pgvector (relational + AI embeddings for documents)
- Jobs: Celery + Redis (background sync jobs, webhook processing)
- Auth: JWT + RBAC (role-based access control)
- LLM Orchestration: Dify Chatflow (primary) + OpenAI (fallback)

**For detailed business context and use cases**, see [BUSINESS.md](BUSINESS.md)

## Ask CFO via Dify (short guide)
Dify is the primary LLM orchestration layer for Ask CFO in this repo: the backend exposes Dify tool endpoints (morning brief, cash forecast, inventory health, payables, doc search) that you import into a Dify Chatflow, and the frontend embeds the Dify chatbot via an iframe using `NEXT_PUBLIC_DIFY_BASE`. There is also a Dify-compatible external knowledge-base retrieval endpoint gated by `dify_external_kb_api_key`. If Dify is not configured, Ask CFO falls back to the local `/chat/ask` path.
1) Expose tool endpoints at `http://127.0.0.1:8100/tools/*` (Docker Compose host port).
2) Open `http://127.0.0.1:8100/openapi.json` and import into Dify as Custom Tool.
   - Server URL (Dify in Docker network): `http://backend:8000`
   - Server URL (Dify on host): `http://127.0.0.1:8100`
3) Configure your Dify Chatflow to call:
   - `/tools/morning-brief`
   - `/tools/cash-forecast`
   - `/tools/inventory-health`
   - `/tools/payables`
   - `/tools/documents/search`
4) Frontend: set `NEXT_PUBLIC_DIFY_BASE` and (optionally) `NEXT_PUBLIC_DIFY_API_KEY`.
5) Ask CFO will call Dify; if `NEXT_PUBLIC_DIFY_BASE` is unset it falls back to `/chat/ask`.

## Start and stop
Start:
```
docker compose up -d --build
```
If you change backend Python code but `docker compose build backend` still shows every layer as **CACHED**, the running container may still use an old image. Use `docker compose build backend --no-cache` (or `docker compose up -d --build --force-recreate backend` after a no-cache build) so the new code is copied into the image.
Note: If `NEXT_PUBLIC_API_BASE` is not set, the frontend uses `window.location.hostname` at runtime to build the API base, which makes the UI portable across machines without rebuilds. For local Docker Compose, set `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8100` and `NEXT_PUBLIC_WISE_API_BASE=http://127.0.0.1:8101` if you want the UI to call local APIs. For remote Dify hosting, keep `NEXT_PUBLIC_DIFY_BASE`/`DIFY_API_URL` set explicitly.
Health checks:
- Backend: `http://127.0.0.1:8100/health`
- Frontend: `http://127.0.0.1:3100/login`
Wise API (separate service on port 8101):
```
http://127.0.0.1:8101/health
```
Stripe API (separate service on port 8102):
```
http://127.0.0.1:8102/health
```
Migrations:
```
docker compose exec backend alembic upgrade head
```
Seed demo data:
```
docker compose exec backend python scripts/seed_demo.py
```
Stop:
```
docker compose down
```

## Default demo login
- Company: Demo Retail Co
- Email: demo@aicfo.dev
- Password: aicfo12345

## Document embeddings (new)
- Upload UI lets you choose an embedding model and chunk size per document.
- Supported embedding models:
  - text-embedding-3-large (better quality, higher cost)
  - text-embedding-3-small (current, cheaper)
  - text-embedding-ada-002 (legacy, generally lower quality than 3-series)
- Chunk size accepted range: 200–5000 characters.
- Reindex existing documents from the Document upload card (queues a background job).

## FX tracked pairs (new)
- Defaults → Tracked currency pairs are stored per company in `company.thresholds.tracked_currency_pairs`.
- Exchange Rates lists and refreshes only those pairs for the active company.

## Wise integration (summary)
- OAuth connection per company and per environment (sandbox/production).
- Tokens and secrets encrypted at rest.
- Supports OAuth or API token auth per environment.
- Syncs profiles, balance accounts, balances, transactions.
- Webhooks trigger incremental refresh.
- Canonical mapping to bank_accounts, bank_balances, bank_transactions.
- Admin UI: `http://127.0.0.1:3100/administrator/wise`.

## Stripe integration (new)
- Full architecture and Stripe object mapping: [docs/stripe-integration.md](docs/stripe-integration.md).
- Admin UI to store Stripe account ID and trigger syncs: `http://127.0.0.1:3100/administrator/stripe`.
- Revenue sync (default 30 days) aggregates balance transactions, charges, and refunds via the `stripe-api` service.
- Balance history + payouts sync includes CSV exports for finance reconciliation.
- True Net Margin metrics pull Stripe fees and net amounts; optionally stored in `stripe_metrics`.
- Backend uses `STRIPE_API_BASE` to call the Stripe API service.
- Configure `stripe-api/.env` with `STRIPE_SECRET_KEY` (required) and `STRIPE_PUBLISHABLE_KEY` (optional).
- Webhooks on the main API: set `STRIPE_WEBHOOK_SECRET` and point Stripe Dashboard to `https://<host>/webhooks/stripe`. Optional `MOCK_STRIPE_WEBHOOK_SECRET` enables `POST /webhooks/stripe/mock` for synthetic payout/refund/failed-charge events (see [docs/stripe-integration.md](docs/stripe-integration.md)).
- **Deploy / Docker:** rebuild `backend` and `worker` after changing webhook or echo env vars (`docker compose build backend worker && docker compose up -d backend worker`). For synthetic merges, optional `STRIPE_API_ECHO_AFTER_SYNTHETIC=true` makes the worker call `GET {STRIPE_API_BASE}/health` (see docs). Ensure `stripe-api` is reachable from those containers (`STRIPE_API_BASE` defaults to `http://stripe-api:8002` in Docker).

### Wise environment variables
Note: Wise credentials are encrypted with RSA using `WISE_PUBLIC_KEY`. The private key `WISE_PRIVATE_KEY` must be stored securely in env.
```
WISE_CLIENT_ID=
WISE_CLIENT_SECRET=
WISE_REDIRECT_URI=http://127.0.0.1:8101/connectors/wise/oauth/callback
WISE_WEBHOOK_URL=http://127.0.0.1:8101/webhooks/wise
WISE_OAUTH_SCOPES_READ=profile balance transactions
WISE_OAUTH_SCOPES_WRITE=transfers
WISE_WRITE_ENABLED=false
WISE_API_BASE_SANDBOX=https://api.sandbox.transferwise.tech
WISE_API_BASE_PRODUCTION=https://api.transferwise.com
WISE_OAUTH_BASE=https://api.transferwise.com
WISE_OAUTH_BASE_SANDBOX=https://api.sandbox.transferwise.tech
WISE_WEBHOOK_SECRET=
ENCRYPTION_KEY=
PRIMARY_COMPANY_ID=
WISE_PUBLIC_KEY=
WISE_PRIVATE_KEY=
WISE_API_TOKEN=
```
Generate RSA keys (2048):
```
python - <<'PY'
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
private_pem = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
public_pem = key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
print("WISE_PRIVATE_KEY=" + private_pem.decode().replace("\n", "\\n"))
print("WISE_PUBLIC_KEY=" + public_pem.decode().replace("\n", "\\n"))
PY
```

## Shopify mock usage
- Shop domain: `mock-shopify:8080`
- Token: `mock_token_123`
- Use Setup page to test connection and sync.

## Known issues and fixes
- Collation mismatch warning: run `ALTER DATABASE ai_cfo REFRESH COLLATION VERSION`.
- Frontend build font failures: use local fonts only (already configured).
- Missing data on dashboard: run Shopify sync and ensure demo seed.
- Worker not starting: check `PRIMARY_COMPANY_ID` empty string; rebuild after updates.

## Q&A
Q: Is this multi-tenant?
A: Yes. All data is scoped by company_id and protected by RBAC.

Q: Where does Wise data show up?
A: In `bank_accounts`, `bank_balances`, and `bank_transactions`, plus raw Wise tables.

Q: How do I refresh Wise data?
A: Use the Wise admin page or `POST /connectors/wise/sync`.

Q: How do I reseed demo data?
A: Run `docker compose exec backend python scripts/seed_demo.py`.

Q: Why is Sales Quality empty?
A: Missing order lines, customer identity, or shipping/currency data. Run Shopify sync.

## API list (core)
Auth
- POST /auth/login
- GET /auth/me
- POST /auth/admin/users
- GET /auth/admin/users?company_id=
- PATCH /auth/admin/users/{user_id}
- DELETE /auth/admin/users/{user_id}

Companies
- GET /companies/public
- GET /companies (Founder-only)
- GET /companies/me
- PATCH /companies/me
- GET /companies/{company_id}
- PATCH /companies/{company_id}
- POST /companies
- DELETE /companies/{company_id}

Metrics
- GET /metrics/morning_brief?date=YYYY-MM-DD
- GET /metrics/sales_quality?start=YYYY-MM-DD&end=YYYY-MM-DD
- GET /metrics/inventory_health
- GET /metrics/cash_forecast?days=7

Payables
- GET /payables

Exchange rates
- GET /exchange-rates
- POST /exchange-rates/refresh
- PATCH /exchange-rates/{pair}

Documents
- POST /imports/docs (form-data: file, embedding_model, chunk_size)
- POST /imports/docs/reindex
- GET /imports/docs
- DELETE /imports/docs/{document_id}

Connectors
- POST /connectors/shopify/test
- POST /connectors/shopify/sync
- Stripe (backend -> stripe-api)
  - GET /connectors/stripe/settings
  - POST /connectors/stripe/settings
  - POST /connectors/stripe/sync-revenue
  - POST /connectors/stripe/balance-payouts
  - POST /connectors/stripe/metrics/true-net-margin
  - POST /connectors/stripe/metrics/true-net-margin/store
  - GET /connectors/stripe/metrics/true-net-margin
  - DELETE /connectors/stripe/metrics/true-net-margin
- Stripe webhooks (main backend, unsigned mock path for dev)
  - POST /webhooks/stripe
  - POST /webhooks/stripe/mock
- (Wise service on http://127.0.0.1:8101)
  - GET /connectors/wise/oauth/start
  - GET /connectors/wise/oauth/callback
  - POST /connectors/wise/disconnect
  - GET /connectors/wise/status
  - POST /connectors/wise/sync
  - GET /connectors/wise/settings
  - PATCH /connectors/wise/settings
  - GET /connectors/wise/test

Webhooks
- (Wise service on http://127.0.0.1:8101)
  - POST /webhooks/wise

Demo data
- POST /demo-data/seed
- DELETE /demo-data/clear

Tools (for Dify)
- GET /tools/morning-brief
- GET /tools/cash-forecast
- GET /tools/inventory-health
- GET /tools/payables
- GET /tools/documents/search

## Runbook (detailed)
Wise connect
1) Set Wise settings in admin UI per environment.
2) Click "Connect Wise" to complete OAuth.
3) Click "Test connection".
4) Trigger sync or wait for webhooks.

Shopify demo data
1) Seed demo data.
2) Open Setup page and connect mock Shopify.
3) Trigger Shopify sync.

Exchange rates
1) Open Exchange Rates page.
2) Click "Capture latest rates".
3) Optional: manual override (Founder/Finance only).
