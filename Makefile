.PHONY: install test dev-backend dev-frontend target demo build

install:
	python -m pip install -e ".[test]"
	cd frontend && npm install

test:
	python -m pytest

dev-backend:
	uvicorn app.main:app --app-dir backend --reload --port 8000

target:
	uvicorn target_app.api.main:app --reload --port 8001

dev-frontend:
	cd frontend && npm run dev

demo:
	python scripts/seed_demo.py

build:
	cd frontend && npm run build

