black:
	pipenv run black --skip-string-normalization app/ tests/

install:
	pipenv install --dev

pycodestyle:
	pipenv run pycodestyle --ignore=E501,W503 app/ tests/

test:
	pipenv run pytest --cache-clear --cov-report term --cov=app/
