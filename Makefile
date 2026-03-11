SHELL := /bin/bash

.PHONY: setup dev etl metrics train test lint

setup:
	docker compose up -d
	cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
	cd frontend && pnpm install

dev:
	docker compose up -d
	cd backend && source venv/bin/activate && uvicorn app.main:app --reload &
	cd frontend && pnpm dev

etl:
	cd backend && source venv/bin/activate && python scripts/run_etl.py --verbose

metrics:
	cd backend && source venv/bin/activate && python scripts/compute_metrics.py --verbose

train:
	cd backend && source venv/bin/activate && python scripts/train_model.py --skip-pinecone --verbose

test:
	cd backend && source venv/bin/activate && python -m pytest -v
	cd frontend && npx tsc --noEmit

lint:
	cd backend && source venv/bin/activate && ruff check .
	cd frontend && npx tsc --noEmit
