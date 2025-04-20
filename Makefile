all: black flake pycodestyle sort test

bandit:
	pipenv run bandit --severity-level high --confidence-level high -r app/ -vvv

black:
	pipenv run black ./

flake:
	pipenv run autoflake --in-place --recursive --remove-all-unused-imports --remove-unused-variables app/*.py tests/*.py

install:
	pipenv install --dev --python 3.13

mypy:
	pipenv run python -m mypy app/ --explicit-package-bases

pycodestyle:
	pipenv run python -m pycodestyle --ignore=E501,W503 app/ tests/

sort:
	pipenv run python -m isort --atomic app/ tests/

test: unit-test integration-test

unit-test:
	pipenv run python -m pytest tests/unit

integration-test:
	pipenv run python -m pytest --cov-fail-under=90 tests/integration