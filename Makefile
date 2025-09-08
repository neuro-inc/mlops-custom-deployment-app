IMAGE_NAME ?= custom-deployment-app-hook
IMAGE_TAG ?= latest
APP_TYPES_REVISION ?= v25.4.3

SHELL := /bin/sh -e

.PHONY: install setup
install setup: poetry.lock
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
	poetry run pytest -vvs --cov=.apolo --cov-report xml:.coverage.unit.xml .apolo/tests/unit

.PHONY: test-integration
test-integration:
	poetry run pytest -vv --cov=.apolo --cov-report xml:.coverage.integration.xml .apolo/tests/integration


.PHONY: build-hook-image
build-hook-image:
	docker build \
		-t $(IMAGE_NAME):latest \
		-f hooks.Dockerfile \
		.;

.PHONY: push-hook-image
push-hook-image:
	docker tag $(IMAGE_NAME):latest ghcr.io/neuro-inc/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push ghcr.io/neuro-inc/$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: gen-types-schemas
gen-types-schemas:
	app-types dump-types-schema .apolo/src/apolo_apps_service_deployment service-deployment ServiceDeploymentInputs .apolo/src/apolo_apps_service_deployment/schemas/ServiceDeploymentInputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_service_deployment service-deployment ServiceDeploymentOutputs .apolo/src/apolo_apps_service_deployment/schemas/ServiceDeploymentOutputs.json

	app-types dump-types-schema .apolo/src/apolo_apps_mlflow_core mlflow MLFlowAppInputs .apolo/src/apolo_apps_mlflow_core/schemas/MLFlowAppInputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_mlflow_core mlflow MLFlowAppOutputs .apolo/src/apolo_apps_mlflow_core/schemas/MLFlowAppOutputs.json
