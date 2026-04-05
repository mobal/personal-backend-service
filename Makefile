.PHONY: all build build-layer build-lambda format install lint bandit test tflint ty

all: bandit format lint test

build: build-layer build-lambda

build-layer:
	./scripts/build_requirements_layer.sh

build-lambda:
	./scripts/build_api.sh

format:
	uv run ruff format app/ tests/

install:
	uv sync

lint:
	uv run ruff check app/ tests/ --fix

bandit:
	uv run -m bandit --severity-level high --confidence-level high -r app/ -vvv

test:
	uv run -m pytest tests --cov=app --cov-report=term-missing --cov-branch

tflint:
	tflint --init
	tflint --chdir=./infrastructure

ty:
	uv run ty check
