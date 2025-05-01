all: black flake pycodestyle sort test

bandit:
	uv run -m bandit --severity-level high --confidence-level high -r app/ -vvv

black:
	uv run -m black ./

flake:
	uv run -m autoflake --in-place --recursive --remove-all-unused-imports --remove-unused-variables app/*.py tests/*.py

install:
	uv sync

mypy:
	uv run -m mypy app/ --explicit-package-bases

pycodestyle:
	uv run -m pycodestyle --ignore=E501,W503 app/ tests/

sort:
	uv run -m isort --atomic app/ tests/

test:
	uv run -m pytest --cov-fail-under=90

unit-test:
	uv run -m pytest tests/unit

integration-test:
	uv run -m pytest tests/integration