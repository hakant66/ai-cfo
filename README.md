# AI Assistant (AI CFO) - Current Status
Last updated: 2026-01-20

## Screenshots
- Dashboard (Morning Brief)
- Sales Quality
- Inventory
- Payables
- Wise Admin (Status + Settings)
- Exchange Rates
- Companies Admin

## Business requirements
- CFO-grade decision system with trusted metrics and provenance.
- Multi-tenant safe from day one (company_id scoped everywhere).
- Role-based access (Founder/Finance/Ops/Marketing/ReadOnly).
- Daily CFO workflows (Morning Brief) plus product analytics (Sales Quality).
- Operational simplicity for a single retailer while remaining tenant-safe.
- Secure integrations with least privilege, token encryption, and auditability.

## Problems solved
- Daily cash visibility and short-term forecast.
- Inventory risk monitoring (stockout/overstock).
- Sales quality insights by channel, customer mix, SKU/category concentration.
- Payables timing for cash planning.
- Exchange rate snapshots with manual overrides (Founder/Finance only).
- Wise connector for bank balances/transactions with OAuth and webhooks.

## Features
- Morning Brief dashboard with cash, sales, payables, alerts.
- Sales Quality page with KPIs, mix, concentration, geography, currency.
- Inventory health monitoring with risk flags.
- Payables table with due date and criticality.
- Ask CFO chat with tool-calling and document search.
- Exchange rates page with live refresh and manual override.
- Wise connector (OAuth, sync, webhook ingestion).
- Admin pages for companies, users, demo data, and Wise settings.

## Solution architecture
- Frontend (Next.js) renders CFO workflows and admin tools.
- Backend (FastAPI) provides REST APIs, auth, and metrics.
- Postgres stores truth data, metrics, and connectors.
- Celery + Redis run background jobs (Shopify sync, Wise sync, doc indexing).
- Mock Shopify service for local demo data.

## Technical stack
- Frontend: Next.js 14 (App Router), TypeScript, Tailwind, shadcn/ui, SWR, Zod
- Backend: FastAPI, SQLAlchemy, Alembic, Pydantic
- Database: Postgres + pgvector
- Jobs: Celery + Redis
- Auth: JWT + RBAC
 - LLM Orchestration: OpenAI (fallback) + Dify Chatflow (primary)

## Ask CFO via Dify (short guide)
1) Expose tool endpoints at `http://127.0.0.1:8000/tools/*` (already wired).
2) Open `http://127.0.0.1:8000/openapi.json` and import into Dify as Custom Tool.
   - Server URL: `http://backend:8000`
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
Note: If `NEXT_PUBLIC_API_BASE` is not set, the frontend uses `window.location.hostname` at runtime to build the API base, which makes the UI portable across machines without rebuilds. For remote Dify hosting, keep `NEXT_PUBLIC_DIFY_BASE`/`DIFY_API_URL` set explicitly.
Health checks:
- Backend: `http://127.0.0.1:8000/health`
- Frontend: `http://127.0.0.1:3000/login`
Wise API (separate service on port 8001):
```
http://127.0.0.1:8001/health
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
- Admin UI: `http://127.0.0.1:3000/administrator/wise`.

### Wise environment variables
Note: Wise credentials are encrypted with RSA using `WISE_PUBLIC_KEY`. The private key `WISE_PRIVATE_KEY` must be stored securely in env.
```
WISE_CLIENT_ID=
WISE_CLIENT_SECRET=
WISE_REDIRECT_URI=http://127.0.0.1:8001/connectors/wise/oauth/callback
WISE_WEBHOOK_URL=http://127.0.0.1:8001/webhooks/wise
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
- (Wise service on http://127.0.0.1:8001)
  - GET /connectors/wise/oauth/start
  - GET /connectors/wise/oauth/callback
  - POST /connectors/wise/disconnect
  - GET /connectors/wise/status
  - POST /connectors/wise/sync
  - GET /connectors/wise/settings
  - PATCH /connectors/wise/settings
  - GET /connectors/wise/test

Webhooks
- (Wise service on http://127.0.0.1:8001)
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
