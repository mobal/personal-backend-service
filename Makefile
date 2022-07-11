autopep8:
	pipenv run autopep8 --in-place --aggressive --aggressive --recursive app/ tests/

install:
	pipenv install

install-dev:
	pipenv install --dev

pycodestyle:
	pipenv run pycodestyle --ignore=E501 app/ tests/

sls-deploy:
	pipenv run sls deploy

test:
	pipenv run pytest --cache-clear --cov-report term --cov=app/