# Argus

Argus is a self-hostable power use reporting platform with:

- **Backend:** Python (FastAPI)
- **Frontend:** React (Vite)
- **Deployment:** Docker images via Docker Compose

## Project structure

- `backend/` — FastAPI service
- `frontend/` — React UI
- `docker-compose.yml` — self-hosted deployment

## Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export ALLOWED_ORIGINS=http://localhost:5173
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

The Vite dev server proxies `/api/*` to `http://localhost:8000`.

## Self-hosting with Docker

```bash
docker compose up --build -d
```

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000/api/v1/health>

The backend CORS policy is configured with `ALLOWED_ORIGINS` (comma-separated).

## Open source best practices

- MIT License (`LICENSE`)
- Contribution guide (`CONTRIBUTING.md`)
- Security policy (`SECURITY.md`)
- Code of conduct (`CODE_OF_CONDUCT.md`)
