# Deployment & Containerization Guide

## 1. Quick Start with Docker Compose

Run the entire system (FastAPI backend + PostgreSQL + Redis + React Dashboard) with one command:

```bash
docker compose up --build -d
```

Access the system at:
- **Operations Dashboard**: `http://localhost:8000`
- **Interactive OpenAPI Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

---

## 2. Environment Configuration (`.env`)

```ini
DATABASE_URL=sqlite:///./reconciliation_engine.db
# Or for production PostgreSQL:
# DATABASE_URL=postgresql://recon_user:recon_pass@postgres:5432/recon_db
REDIS_URL=redis://localhost:6379/0
ENVIRONMENT=production
LOG_LEVEL=INFO
TOLERANCE_AMOUNT=0.01
TOLERANCE_FX=0.015
```

---

## 3. Local Development (Without Docker)

### Backend:
```bash
py -m pip install -r requirements.txt
py -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Running Test Suite:
```bash
py -m pytest backend/tests -v --cov=backend/app
```
