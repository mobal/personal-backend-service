all: ruff flake pycodestyle sort test

bandit:
	uv run -m bandit --severity-level high --confidence-level high -r app/ -vvv

flake:
	uv run -m autoflake --in-place --recursive --remove-all-unused-imports --remove-unused-variables app/*.py tests/*.py

install:
	uv sync

mypy:
	uv run -m mypy app/ --explicit-package-bases

pycodestyle:
	uv run -m pycodestyle --ignore=E501,W503 app/ tests/

ruff:
	uv run -m ruff check --fix

serve:
	uv run -m uvicorn app.api_handler:app

sort:
	uv run -m ruff check --select I --fix

test:
	uv run -m pytest --cov-fail-under=90

unit-test:
	uv run -m pytest tests/unit

upgrade:
	uv sync --upgrade

integration-test:
	uv run -m pytest tests/integration