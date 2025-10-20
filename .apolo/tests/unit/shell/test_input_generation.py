import json

from apolo_app_types_fixtures.constants import (
    APP_ID,
    APP_SECRETS_NAME,
    DEFAULT_CLUSTER_NAME,
    DEFAULT_NAMESPACE,
    DEFAULT_ORG_NAME,
    DEFAULT_PROJECT_NAME,
)
from apolo_apps_service_deployment import (
    ServiceDeploymentIngress,
    ServiceDeploymentInputs,
    ServiceDeploymentInputsProcessor,
)
from apolo_apps_shell.inputs_processor import ShellAppChartValueProcessor

from apolo_app_types import ShellAppInputs
from apolo_app_types.app_types import AppType
from apolo_app_types.protocols.common import ContainerImage, Preset
from apolo_app_types.protocols.custom_deployment import NetworkingConfig


async def test_shell_values_generation(setup_clients):
    apolo_client = setup_clients
    input_processor = ShellAppChartValueProcessor(client=apolo_client)
    helm_params = await input_processor.gen_extra_values(
        input_=ShellAppInputs(
            preset=Preset(name="cpu-small"),
        ),
        apolo_client=setup_clients,
        app_type=AppType.Shell,
        app_name="shell-app",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )
    assert helm_params["image"] == {
        "repository": "ghcr.io/neuro-inc/web-shell",
        "tag": "pipelines",
        "pullPolicy": "IfNotPresent",
    }

    assert helm_params["service"] == {
        "enabled": True,
        "ports": [{"containerPort": 7681, "name": "http"}],
    }

    assert "podAnnotations" in helm_params
    annotations = helm_params["podAnnotations"]
    assert "platform.apolo.us/inject-storage" in annotations

    storage_json = annotations["platform.apolo.us/inject-storage"]
    parsed_storage = json.loads(storage_json)
    assert len(parsed_storage) == 1

    assert parsed_storage[0]["storage_uri"] == (
        f"storage://{DEFAULT_CLUSTER_NAME}/{DEFAULT_ORG_NAME}/{DEFAULT_PROJECT_NAME}/"
        f".apps/shell/shell-app"
    )
    assert parsed_storage[0]["mount_path"] == "/var/storage"
    assert parsed_storage[0]["mount_mode"] == "r"

    pod_labels = helm_params.get("podLabels", {})
    assert pod_labels.get("platform.apolo.us/inject-storage") == "true"


async def test_service_deployment_values_generation_with_ingress_annotations(
    setup_clients,
):
    apolo_client = setup_clients
    input_processor = ServiceDeploymentInputsProcessor(client=apolo_client)

    ingress_annotations = {
        "traefik.ingress.kubernetes.io/request-buffering": "false",
        "traefik.ingress.kubernetes.io/response-buffering": "false",
    }

    service_inputs = ServiceDeploymentInputs(
        preset=Preset(name="cpu-small"),
        image=ContainerImage(repository="test-repo", tag="latest"),
        networking=NetworkingConfig(
            service_enabled=True,
            ingress_http=ServiceDeploymentIngress(annotations=ingress_annotations),
        ),
    )

    helm_params = await input_processor.gen_extra_values(
        input_=service_inputs,
        apolo_client=apolo_client,
        app_type=AppType.Shell,
        app_name="shell-app",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    ingress = helm_params.get("ingress", {})
    assert "annotations" in ingress
    for k, v in ingress_annotations.items():
        assert ingress["annotations"][k] == v
