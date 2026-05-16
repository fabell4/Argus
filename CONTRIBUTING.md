# Contributing

Thanks for contributing to Argus.

## Development setup

- Backend: Python 3.11+
- Frontend: Node.js 22+

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
ruff check .
```

### Frontend

```bash
cd frontend
npm ci
npm run lint
npm run build
```

## Pull requests

- Keep changes focused and small.
- Add or update tests for behavioral changes.
- Ensure lint, tests, and build commands pass before review.
