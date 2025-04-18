IMAGE_NAME ?= post-deployment-app-service-deployment-hook
APP_TYPES_REVISION ?= v25.4.3

SHELL := /bin/sh -e

.PHONY: install
install: poetry.lock
	poetry config virtualenvs.in-project true
	poetry install --with dev
	poetry run pre-commit install;

.PHONY: install-app-types
install-app-types:
	poetry run pip install --force-reinstall -U git+https://${APOLO_GITHUB_TOKEN}@github.com/neuro-inc/app-types.git@${APP_TYPES_REVISION}

.PHONY: format
format:
ifdef CI
	poetry run pre-commit run --all-files --show-diff-on-failure
else
	# automatically fix the formatting issues and rerun again
	poetry run pre-commit run --all-files || poetry run pre-commit run --all-files
endif

.PHONY: lint
lint: format
	poetry run mypy .apolo

.PHONY: test-unit
test-unit:
	poetry run pytest -vvs --cov=platform_apps --cov-report xml:.coverage.unit.xml .apolo/tests/unit

.PHONY: test-integration
test-integration:
	poetry run pytest -vv --cov=platform_apps --cov-report xml:.coverage.integration.xml .apolo/tests/integration


.PHONY: build-hook-image
build-hook-image:
	docker build \
		-t $(IMAGE_NAME):latest \
		-f post-installation.Dockerfile \
		.;
