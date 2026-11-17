.PHONY: help all build build-layer build-lambda format install lint bandit test tflint ty

.DEFAULT_GOAL := help

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

all: bandit format lint test ## Run bandit, format, lint and tests

build: build-layer build-lambda ## Build the Lambda layer and API ZIPs (needs Docker)

build-layer: ## Build dist/requirements.zip (Lambda layer) in the Lambda image
	./scripts/build_requirements_layer.sh

build-lambda: ## Build dist/api.zip (application code) in the Lambda image
	./scripts/build_api.sh

format: ## Format app/ and tests/ with ruff
	uv run ruff format app/ tests/

install: ## Install dependencies from uv.lock
	uv sync

lint: ## Lint app/ and tests/ with ruff (applies safe fixes)
	uv run ruff check app/ tests/ --fix

bandit: ## Scan app/ for security issues (high severity/confidence)
	uv run -m bandit --severity-level high --confidence-level high -r app/ -vvv

test: ## Run the tests with branch coverage
	uv run -m pytest tests --cov=app --cov-report=term-missing --cov-branch

tflint: ## Lint the Terraform/OpenTofu code in infrastructure/
	tflint --init
	tflint --chdir=./infrastructure

ty: ## Type-check app/ with ty
	uv run ty check app/
