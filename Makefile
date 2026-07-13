.PHONY: setup backend frontend dev test lint build fixtures

# One-time setup: backend venv + frontend node_modules
setup:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	cd frontend && npm install

# Run the FastAPI backend on :8000
backend:
	cd backend && .venv/bin/uvicorn app.api.main:app --reload --port 8000

# Run the Next.js frontend on :3000
frontend:
	cd frontend && npm run dev

# Run both (backend in background; Ctrl-C stops both)
dev:
	@trap 'kill 0' INT TERM; \
	(cd backend && .venv/bin/uvicorn app.api.main:app --port 8000 &) ; \
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/python -m pytest -q
	cd frontend && npm run test -- --run

lint:
	cd backend && .venv/bin/ruff check app tests scripts && .venv/bin/python -m mypy app
	cd frontend && npm run lint

build:
	cd frontend && npm run build

# Re-record demo fixtures from live yfinance (requires network)
fixtures:
	cd backend && .venv/bin/python scripts/record_fixtures.py
