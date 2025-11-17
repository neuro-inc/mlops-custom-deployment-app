IMAGE_NAME ?= mlops-custom-deployment-app
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
	app-types dump-types-schema .apolo/src/apolo_apps_service_deployment ServiceDeploymentInputs .apolo/src/apolo_apps_service_deployment/schemas/ServiceDeploymentInputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_service_deployment ServiceDeploymentOutputs .apolo/src/apolo_apps_service_deployment/schemas/ServiceDeploymentOutputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_mlflow_core MLFlowAppInputs .apolo/src/apolo_apps_mlflow_core/schemas/MLFlowAppInputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_mlflow_core MLFlowAppOutputs .apolo/src/apolo_apps_mlflow_core/schemas/MLFlowAppOutputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_shell ShellAppInputs .apolo/src/apolo_apps_shell/schemas/ShellAppInputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_shell ShellAppOutputs .apolo/src/apolo_apps_shell/schemas/ShellAppOutputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_vscode VSCodeAppInputs .apolo/src/apolo_apps_vscode/schemas/VSCodeAppInputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_vscode VSCodeAppOutputs .apolo/src/apolo_apps_vscode/schemas/VSCodeAppOutputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_openwebui OpenWebUIAppInputs .apolo/src/apolo_apps_openwebui/schemas/OpenWebUIAppInputs.json
	app-types dump-types-schema .apolo/src/apolo_apps_openwebui OpenWebUIAppOutputs .apolo/src/apolo_apps_openwebui/schemas/OpenWebUIAppOutputs.json
