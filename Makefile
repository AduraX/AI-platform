SHELL := /bin/bash

PYTHON ?= python3
UVICORN ?= uvicorn
NPM ?= npm
UV ?= uv

.PHONY: install-python install-frontend lock dev-python dev-frontend test lint fmt docker-up docker-down

install-python:
	$(UV) sync --all-packages --group dev

install-frontend:
	cd apps/frontend && $(NPM) install

lock:
	$(UV) lock

dev-python:
	@echo "Run each service in its own shell:"
	@echo "cd services/api-gateway && $(UV) run $(UVICORN) api_gateway.main:app --reload --port 8000"
	@echo "cd services/chat-service && $(UV) run $(UVICORN) chat_service.main:app --reload --port 8002"
	@echo "cd services/rag-service && $(UV) run $(UVICORN) rag_service.main:app --reload --port 8003"
	@echo "cd services/ingestion-service && $(UV) run $(UVICORN) ingestion_service.main:app --reload --port 8004"
	@echo "cd services/ocr-service && $(UV) run $(UVICORN) ocr_service.main:app --reload --port 8005"
	@echo "cd services/model-router && $(UV) run $(UVICORN) model_router.main:app --reload --port 8006"
	@echo "cd services/eval-service && $(UV) run $(UVICORN) eval_service.main:app --reload --port 8007"

dev-frontend:
	cd apps/frontend && $(NPM) run dev

test:
	cd shared/python-common && $(UV) run pytest tests
	cd services/api-gateway && $(UV) run pytest tests
	cd services/chat-service && $(UV) run pytest tests
	cd services/rag-service && $(UV) run pytest tests
	cd services/ingestion-service && $(UV) run pytest tests
	cd services/ocr-service && $(UV) run pytest tests
	cd services/model-router && $(UV) run pytest tests
	cd services/eval-service && $(UV) run pytest tests

lint:
	$(UV) run ruff check services shared/python-common

fmt:
	$(UV) run ruff format services shared/python-common

docker-up:
	docker compose up -d

docker-down:
	docker compose down
