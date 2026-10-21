.PHONY: up down test lint dev-backend dev-frontend help

help:
	@echo "System Design Simulator Makefile"
	@echo "Targets:"
	@echo "  make up           Start all services in Docker Compose (daemon mode)"
	@echo "  make down         Stop all Docker Compose services"
	@echo "  make test         Run backend unit tests with pytest"
	@echo "  make lint         Run backend linting"
	@echo "  make dev-backend  Run backend locally with Flask"
	@echo "  make dev-frontend Run frontend locally with Vite"

up:
	docker compose up --build -d

down:
	docker compose down

test:
	pytest backend/tests

lint:
	flake8 backend || echo "flake8 finished"

dev-backend:
	cd backend && python app.py

dev-frontend:
	cd frontend && npm run dev
