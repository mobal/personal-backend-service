black:
	pipenv run black --skip-string-normalization app/ tests/

deploy:
	pipenv run sls deploy

install:
	pipenv install --dev
	npm i

pycodestyle:
	pipenv run python -m pycodestyle --ignore=E501,W503 app/ tests/

test:
	pipenv run python -m pytest --cache-clear --cov-report term --cov=app/
