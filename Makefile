.PHONY: up down logs dev test

up:
	cp -n .env.example .env || true
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -q
