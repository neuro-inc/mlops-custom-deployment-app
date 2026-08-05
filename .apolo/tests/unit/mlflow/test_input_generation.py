import pytest
from apolo_app_types_fixtures.constants import (
    APP_ID,
    APP_SECRETS_NAME,
    DEFAULT_NAMESPACE,
    DEFAULT_POSTGRES_CREDS,
)
from apolo_apps_mlflow_core.inputs_processor import MLFlowChartValueProcessor
from apolo_apps_mlflow_core.types import (
    MLFlowAppInputs,
    MLFlowMetadataPostgres,
    MLFlowMetadataSQLite,
)

from apolo_app_types.protocols.common import (
    ApoloFilesPath,
    ApoloSecret,
    IngressHttp,
    Preset,
)


@pytest.mark.asyncio
async def test_values_mlflow_generation_default_sqlite(
    setup_clients, mock_get_preset_cpu
):
    """
    Test that MLFlow defaults to sqlite:// and the default PVC name
    when no metadata_storage is provided.
    """
    input_data = MLFlowAppInputs(
        preset=Preset(name="cpu-small"),
        ingress_http=IngressHttp(clusterName="test"),
        metadata_storage=MLFlowMetadataSQLite(),
        artifact_store=ApoloFilesPath(
            path="storage://test-cluster/myorg/proj/mlflow-artifacts"
        ),
    )

    # Create the processor instance with the client
    processor = MLFlowChartValueProcessor(client=setup_clients)

    # Call gen_extra_values directly
    helm_params = await processor.gen_extra_values(
        input_=input_data,
        app_name="my-mlflow",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    # Confirm environment var MLFLOW_TRACKING_URI = sqlite://...
    env_vars = helm_params["container"]["env"]
    tracking_env = next(
        (e for e in env_vars if e["name"] == "MLFLOW_TRACKING_URI"), None
    )
    assert tracking_env["value"] == "sqlite:///mlflow-data/mlflow.db"

    # Confirm we have a PVC volume mount
    assert "volumes" in helm_params
    assert len(helm_params["volumes"]) == 1
    assert helm_params["volumes"][0]["name"] == "mlflow-db-pvc"
    assert (
        helm_params["volumes"][0]["persistentVolumeClaim"]["claimName"]
        == f"mlflow-sqlite-storage-{APP_ID}"
    )

    assert "volumeMounts" in helm_params
    assert len(helm_params["volumeMounts"]) == 1
    assert helm_params["volumeMounts"][0]["name"] == "mlflow-db-pvc"
    assert helm_params["volumeMounts"][0]["mountPath"] == "/mlflow-data"

    # Confirm artifact store configuration
    artifact_env = next(
        (e for e in env_vars if e["name"] == "MLFLOW_ARTIFACT_ROOT"), None
    )
    assert artifact_env is not None
    assert artifact_env["value"] == "file:///mlflow-artifacts"

    # Confirm service is 5000
    assert helm_params["service"]["ports"][0]["containerPort"] == 5000
    # Confirm "application=mlflow" label
    assert helm_params["labels"]["application"] == "mlflow"

    # Verify MLflow gets ONLY auth middleware (no strip headers)
    assert (
        helm_params["ingress"]["annotations"][
            "traefik.ingress.kubernetes.io/router.middlewares"
        ]
        == "platform-platform-control-plane-ingress-auth@kubernetescrd"
    )


@pytest.mark.asyncio
async def test_values_mlflow_generation_sqlite_explicit_no_pvc_name(
    setup_clients, mock_get_preset_cpu
):
    """
    Test that MLFlow uses the default PVC name when SQLite is chosen
    but no pvc_name is provided.
    """
    input_data = MLFlowAppInputs(
        preset=Preset(name="cpu-small"),
        ingress_http=IngressHttp(clusterName="test"),
        metadata_storage=MLFlowMetadataSQLite(),
        artifact_store=ApoloFilesPath(path="storage://foo/bar/baz"),
    )

    # Create the processor instance with the client
    processor = MLFlowChartValueProcessor(client=setup_clients)

    # Call gen_extra_values directly
    helm_params = await processor.gen_extra_values(
        input_=input_data,
        app_name="my-mlflow",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    # Assert SQLite URI
    env_vars = helm_params["container"]["env"]
    tracking_env = next(
        (e for e in env_vars if e["name"] == "MLFLOW_TRACKING_URI"), None
    )
    assert tracking_env["value"] == "sqlite:///mlflow-data/mlflow.db"

    # Assert default PVC name
    assert (
        helm_params["volumes"][0]["persistentVolumeClaim"]["claimName"]
        == f"mlflow-sqlite-storage-{APP_ID}"
    )


@pytest.mark.asyncio
async def test_values_mlflow_generation_postgres_uri(
    setup_clients, mock_get_preset_cpu
):
    """
    Test that MLFlow config uses Postgres credentials
    when provided.
    """
    # Create credentials with URI populated
    postgres_creds = DEFAULT_POSTGRES_CREDS.model_copy(
        update={
            "pgbouncer_uri": ApoloSecret(key="mlflow-pgbouncer-uri"),
            "postgres_uri": ApoloSecret(key="mlflow-postgres-uri"),
        }
    )

    input_data = MLFlowAppInputs(
        preset=Preset(name="cpu-small"),
        ingress_http=IngressHttp(clusterName="test-cluster"),
        metadata_storage=MLFlowMetadataPostgres(
            postgres_credentials=postgres_creds,
        ),
        artifact_store=ApoloFilesPath(
            path="storage://test-cluster/myorg/proj/mlflow-artifacts"
        ),
    )

    # Create the processor instance with the client
    processor = MLFlowChartValueProcessor(client=setup_clients)

    # Call gen_extra_values directly
    helm_params = await processor.gen_extra_values(
        input_=input_data,
        app_name="my-mlflow",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    # Check environment var for PG URI - should be an ApoloSecret reference
    env_vars = helm_params["container"]["env"]
    tracking_env = next(
        (e for e in env_vars if e["name"] == "MLFLOW_TRACKING_URI"), None
    )
    assert tracking_env is not None
    # Should be a secret reference dict pointing to pgbouncer_uri (prioritized)
    assert isinstance(tracking_env["value"], dict)
    assert "valueFrom" in tracking_env["value"]
    assert "secretKeyRef" in tracking_env["value"]["valueFrom"]
    assert (
        tracking_env["value"]["valueFrom"]["secretKeyRef"]["key"]
        == "mlflow-pgbouncer-uri"
    )

    # No PVC volumes
    assert "volumes" not in helm_params
    assert "volumeMounts" not in helm_params

    # Confirm artifact store configuration
    artifact_env = next(
        (e for e in env_vars if e["name"] == "MLFLOW_ARTIFACT_ROOT"), None
    )
    assert artifact_env is not None
    assert artifact_env["value"] == "file:///mlflow-artifacts"

    assert helm_params["labels"]["application"] == "mlflow"


@pytest.mark.asyncio
async def test_values_mlflow_allowed_hosts_and_jobs_disabled(
    setup_clients, mock_get_preset_cpu
):
    """
    MLflow 3.x answers 403 for any Host header it does not recognise, and its
    defaults cover only loopback and private IPs — which the kubelet probes
    satisfy while real traffic does not. Setting MLFLOW_SERVER_ALLOWED_HOSTS
    replaces those defaults rather than extending them, so the generated list
    has to carry the ingress hostname, the in-cluster service name and the
    original defaults all at once.
    """
    input_data = MLFlowAppInputs(
        preset=Preset(name="cpu-small"),
        ingress_http=IngressHttp(clusterName="test"),
        metadata_storage=MLFlowMetadataSQLite(),
        artifact_store=ApoloFilesPath(
            path="storage://test-cluster/myorg/proj/mlflow-artifacts"
        ),
    )
    processor = MLFlowChartValueProcessor(client=setup_clients)
    helm_params = await processor.gen_extra_values(
        input_=input_data,
        app_name="my-mlflow",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    env_vars = helm_params["container"]["env"]
    allowed_env = next(
        (e for e in env_vars if e["name"] == "MLFLOW_SERVER_ALLOWED_HOSTS"), None
    )
    assert allowed_env is not None
    allowed = allowed_env["value"].split(",")

    # probes address the pod IP, so the private-IP defaults must survive
    assert "10.*" in allowed
    assert "localhost" in allowed

    # clients running as platform jobs reach the service by its in-cluster name,
    # and send a port in the Host header
    assert f"*.{DEFAULT_NAMESPACE}" in allowed
    assert f"*.{DEFAULT_NAMESPACE}:*" in allowed

    # the UI is served on the ingress hostname
    ingress_hosts = [h["host"] for h in helm_params["ingress"]["hosts"]]
    assert ingress_hosts
    for host in ingress_hosts:
        assert host in allowed
        assert f"{host}:*" in allowed

    jobs_env = next(
        (e for e in env_vars if e["name"] == "MLFLOW_SERVER_ENABLE_JOB_EXECUTION"),
        None,
    )
    assert jobs_env is not None
    assert jobs_env["value"] == "false"
