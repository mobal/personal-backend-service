all: black flake pycodestyle sort test

black:
	pipenv run black --skip-string-normalization ./

deploy:
	pipenv run npx sls deploy

flake:
	pipenv run autoflake --in-place --remove-unused-variables app/*.py tests/*.py

install: install-python install-node

install-node:
	npm i --include=dev

install-python:
	pipenv install --dev --python 3.12

pycodestyle:
	pipenv run python -m pycodestyle --ignore=E501,W503 app/ tests/

sort:
	pipenv run python -m isort --atomic app/ tests/

test:
	pipenv run python -m pytest
