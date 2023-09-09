VENV_NAME = venv
VENV_PYTHON = $(VENV_NAME)/bin/python


clean:
	rm -rf ${VENV_NAME}

venv: clean
	python -m venv ${VENV_NAME} && \
	${VENV_PYTHON} -m pip install --upgrade pip && \
	${VENV_PYTHON} -m pip install -e ".[testing,docs]"

serve:
	${VENV_PYTHON} -m mkdocs serve

build:
	${VENV_PTYHON} -m mkdocs build

gh-deploy:
	${VENV_PYTHON} -m mkdocs gh-deploy --force
