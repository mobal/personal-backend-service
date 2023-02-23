black:
	python3 -m pipenv run black --skip-string-normalization ./

deploy:
	python3 -m pipenv run sls deploy

install:
	python3 -m pipenv install --dev
	npm i

pycodestyle:
	python3 -m pipenv run python -m pycodestyle --ignore=E501,W503 app/ tests/

sort:
	python3 -m pipenv run python -m isort --atomic app/ tests/

test:
	python3 -m pipenv run python -m pytest --cache-clear --cov-report term --cov=app/
