# App development in this repository

Follow the [shared App creation and deployment flow](../../../apolo-agent-harness/docs/engineering/app-development.md) for common contracts, template discovery, installation, and Dev/Prod promotion. The link assumes sibling checkouts; use the harness location configured by setup when working elsewhere.

## Repository-specific implementation

- This repository contains a generic application Helm chart and several predefined Apps. Inspect [the manifest](../../.apolo/applications.yaml), [charts](../../charts/), and the [Service Deployment package](../../.apolo/src/apolo_apps_service_deployment) for a working example.
- `CustomDeploymentChartValueProcessor` is a shared processor used here and by other App repositories. Preserve its consumer contracts when changing it; App-specific behavior belongs in the relevant subclass.
- [pyproject.toml](../../pyproject.toml) registers the `.apolo` packages. [hooks.Dockerfile](../../hooks.Dockerfile) packages them with `apolo-app-types` and uses the shared entrypoint.

## Validate source and contracts

Use this repository's supported Python/Poetry versions and configured development environment. Run from the repository root:

```sh
poetry run make gen-types-schemas
make lint
make test-unit
```

Review generated changes; `make lint` includes formatting hooks that can modify files. Follow [the test workflow](../../.github/workflows/test.yaml) for required checks and prepare the configured environment before integration tests.

The [schema-generation hook](../../.pre-commit-config.yaml) runs `make gen-types-schemas`. Add new model/schema pairs to [the Makefile](../../Makefile) and commit the generated files.

[The golden render test](../../.apolo/tests/unit/chart/test_golden_render.py) runs each App's processor on its cases, renders `charts/custom-deployment` with `helm template` and compares the output with [the goldens](../../.apolo/tests/unit/chart/goldens). Chart branches that no App reaches are rendered from hand-written values in `RAW_CASES`. Locally it is skipped without `helm` on `PATH`; CI installs Helm v3.22.1 and fails the test if Helm is missing. A new App on this chart needs a case there. After an intended chart or processor change, run `make update-goldens` and review the golden diff before committing it.

## Processor image publication

[This repository's CI](../../.github/workflows/ci.yaml) checks the source and builds `ghcr.io/neuro-inc/mlops-custom-deployment-app`:

| Source event | Processor image tag |
| --- | --- |
| Non-Dependabot pull request targeting `master` | Lowercased branch name, with characters outside `a-z0-9_.-` replaced by `-`. |
| Push to `master` | `master`. |
| Push of a `v*` tag | The exact Git tag, including `v`. |
