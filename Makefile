# DMS — Makefile d'orchestration Docker
# Prereqis : Docker Desktop, docker compose v2
#
# Commandes principales :
#   make up        — lance Postgres + migrations + stack complete
#   make down      — arrete tout
#   make test      — execute les tests dans le container API
#   make lint      — ruff + black check
#   make logs      — suit les logs en temps reel
#   make migrate   — applique les migrations Alembic
#   make status    — etat des services
#   make ocr-batch — lance le bridge OCR sur un dossier

.PHONY: up down restart test lint logs migrate status health ocr-batch clean db-shell

# ── Stack lifecycle ──────────────────────────────────────────────────────

up: ## Lance Postgres, migrations, puis la stack complete
	docker compose up -d postgres
	@echo ":: Attente Postgres healthy..."
	@docker compose exec postgres pg_isready -U dms -q || (sleep 3 && docker compose exec postgres pg_isready -U dms)
	docker compose run --rm --no-deps migrate
	docker compose --profile full up -d
	@echo ":: Stack DMS demarree. API=:8000  Backend=:9090  LS=:8080"

down: ## Arrete tous les services
	docker compose --profile full --profile tools down

restart: down up ## Redemarrage complet

# ── Migrations ───────────────────────────────────────────────────────────

migrate: ## Applique alembic upgrade head
	docker compose up -d postgres
	docker compose run --rm --no-deps migrate

# ── Tests & Lint ─────────────────────────────────────────────────────────

test: ## Execute pytest dans le container API
	docker compose --profile full exec api python -m pytest tests/ -x --tb=short -q

lint: ## Ruff + Black check (local, pas dans Docker)
	python -m ruff check src tests services
	python -m black --check src tests services

# ── Observabilite ────────────────────────────────────────────────────────

logs: ## Suit les logs de tous les services
	docker compose --profile full logs -f

status: ## Etat des services Docker
	docker compose --profile full ps

health: ## Verifie la sante des endpoints
	@echo ":: API /health"
	@curl -sf http://localhost:8000/health 2>/dev/null || echo "  API non disponible"
	@echo ""
	@echo ":: API /api/health (avec DB)"
	@curl -sf http://localhost:8000/api/health 2>/dev/null || echo "  API+DB non disponible"
	@echo ""
	@echo ":: Annotation Backend /health"
	@curl -sf http://localhost:9090/health 2>/dev/null || echo "  Backend non disponible"
	@echo ""
	@echo ":: Label Studio :8080"
	@curl -sf http://localhost:8080/health 2>/dev/null || echo "  Label Studio non disponible"

# ── OCR / Ingestion ─────────────────────────────────────────────────────

SRC ?= data/uploads
OUT ?= data/ingest/batch_output

ocr-batch: ## Lance le bridge OCR. Usage: make ocr-batch SRC=path/to/pdfs
	docker compose --profile full exec api python scripts/ingest_to_annotation_bridge.py \
		--source-root /app/$(SRC) \
		--output-root /app/$(OUT) \
		--cloud-first

# ── Utilitaires ──────────────────────────────────────────────────────────

db-shell: ## Ouvre un psql dans le container Postgres
	docker compose exec postgres psql -U dms -d dms

clean: ## Supprime les volumes Docker (ATTENTION: perte de donnees)
	docker compose --profile full --profile tools down -v
	@echo ":: Volumes supprimes. make up pour reconstruire."
