# AI CFO MVP

## Architecture Overview
The AI CFO MVP is organized into four layers that align with CFO-grade decision workflows:

1. **Truth layer**: SQLAlchemy models capture canonical retail data (orders, inventory, bank, payables, POs). Metrics returned by the API include currency, time window, provenance, source systems, and last refresh.
2. **Finance brain**: Rule-based services compute cash forecasts, weeks of cover, and alert triggers. These outputs are persisted through `metric_runs` and surfaced through API endpoints.
3. **CFO workflows**: FastAPI endpoints deliver the Morning CFO Brief, inventory health, and payables scheduling. Celery workers handle sync and recompute jobs.
4. **Conversation layer**: `/chat/ask` orchestrates tool outputs and builds a narrative response that only reflects verified metrics.

The system is deployed via Docker Compose with Postgres and Redis, a FastAPI backend, a Celery worker, and a Next.js 14 frontend.

## Repository Structure
```
_ai-cfo/
  backend/
    alembic/
    app/
    tests/
  frontend/
    app/
    components/
  templates/
  docker-compose.yml
```

## Running Locally

1. Copy environment files:
   ```bash
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   ```
2. Start services:
   ```bash
   docker compose up --build
   ```
3. Apply migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```
4. Seed demo data (optional):
   ```bash
   docker compose exec backend python -c "from app.db.session import SessionLocal; from app.utils.demo_seed import seed_demo_company; db=SessionLocal(); seed_demo_company(db)"
   ```
5. Visit:
   - Frontend: http://localhost:3000
   - Backend API docs: http://localhost:8000/docs

## CSV Templates
Templates are available in the `templates/` directory:
- `bank.csv`
- `payables.csv`
- `purchase_orders.csv`

## Tests
```bash
docker compose exec backend pytest
```

## How to Extend
- **Xero/QB connector**: Implement `AccountingConnector` and add OAuth + data ingestion into `bills` and `bank_transactions`.
- **Open Banking connector**: Add a banking connector that maps transactions into `bank_transactions` and account balances into `bank_accounts`.
- **Meta/Klaviyo**: Extend the marketing connector to ingest spend and campaign metrics into a `marketing_spend` table.
