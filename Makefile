.DEFAULT_GOAL := help

SRC         := app/ tests/
TESTS       ?= tests
BRUNO_IMAGE := usebruno/cli:4.3.0

.PHONY: help install \
	format format-check lint fix ty bandit tflint check \
	test test-fast \
	up down e2e \
	build build-layer build-lambda upload-layer upload-api \
	clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make \033[36m<target>\033[0m\n"} \
		/^##@ / {printf "\n\033[1m%s\033[0m\n", substr($$0, 5)} \
		/^[a-zA-Z0-9_-]+:.*## / {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

##@ Setup

install: ## Install dependencies from uv.lock
	uv sync

##@ Quality

format: ## Format app/ and tests/ with ruff (rewrites files)
	uv run ruff format $(SRC)

format-check: ## Check the formatting without changing files
	uv run ruff format --check $(SRC)

lint: ## Lint app/ and tests/ with ruff (no changes)
	uv run ruff check $(SRC) --statistics

fix: ## Format and apply safe ruff lint fixes
	uv run ruff format $(SRC)
	uv run ruff check $(SRC) --fix

ty: ## Type-check app/ with ty
	uv run ty check app/

bandit: ## Scan app/ for security issues (high severity/confidence)
	uv run -m bandit --severity-level high --confidence-level high -r app/ -vvv

tflint: ## Lint the Terraform/OpenTofu code in infrastructure/
	tflint --init
	tflint --chdir=./infrastructure

check: bandit format-check lint ty test ## Run the static checks and the tests, like CI (no file changes)

##@ Tests

test: ## Run the tests in parallel with branch coverage (TESTS=tests/unit to narrow)
	uv run rstest $(TESTS) -n auto --cov=app --cov-branch --cov-report=term-missing

test-fast: ## Run the tests in parallel without coverage (TESTS=tests/unit to narrow)
	uv run rstest $(TESTS)

##@ Docker

up: ## Start the AWS Emulator and the app with docker compose (http://localhost:8080)
	docker compose up -d --build --wait --wait-timeout 300 app

down: ## Stop the docker compose stack and drop its volumes
	docker compose down -v --remove-orphans

e2e: up ## Run the Bruno collection against the compose stack (run `make down` after)
	docker run --rm --network "container:$$(docker compose ps -q emulator)" \
		-v "$(CURDIR)/collections:/bruno:ro" \
		$(BRUNO_IMAGE) run --env e2e -r \
		--env-var baseUrl=http://localhost:8080 --insecure

##@ Build & deploy

build: build-layer build-lambda ## Build the Lambda layer and API ZIPs (needs Docker)

build-layer: ## Build dist/requirements.zip (Lambda layer) in the Lambda image
	./scripts/build_requirements_layer.sh

build-lambda: ## Build dist/api.zip (application code) in the Lambda image
	./scripts/build_api.sh

upload-layer: ## Upload dist/requirements.zip to the artifacts bucket (needs AWS credentials)
	./scripts/upload_requirements_layer.sh

upload-api: ## Upload dist/api.zip to the artifacts bucket (needs AWS credentials)
	./scripts/upload_api.sh

##@ Housekeeping

clean: ## Remove test, coverage and linter caches (dist/ is kept)
	rm -rf .coverage .coverage.* coverage.xml .rstest_cache .pytest_cache .ruff_cache
