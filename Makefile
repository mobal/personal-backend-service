all: format lint test

bandit:
	uv run -m bandit --severity-level high --confidence-level high -r app/

format:
	uv run -m ruff format .

install:
	uv sync

lint:
	uv run -m ruff check app/ tests/ --fix

mypy:
	uv run -m mypy app/ --explicit-package-bases

serve:
	uv run -m uvicorn app.api_handler:app

test:
	uv run -m pytest --cov-fail-under=90 --cov-report=term --cov=app/ tests/

unit-test:
	uv run -m pytest tests/unit

upgrade:
	uv sync --upgrade

integration-test:
	uv run -m pytest tests/integration
