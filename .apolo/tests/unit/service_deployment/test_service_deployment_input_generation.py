import json
from pathlib import Path

import pytest
from apolo_app_types_fixtures.constants import (
    APP_ID,
    APP_SECRETS_NAME,
    DEFAULT_NAMESPACE,
)
from apolo_apps_service_deployment.inputs_processor import (
    ServiceDeploymentInputsProcessor,
)
from apolo_apps_service_deployment.types import ServiceDeploymentInputs
from apolo_sdk import Client

from apolo_app_types.protocols.common import (
    ContainerImage,
    InitContainer,
    Preset,
)


def test_routing_input_contract_is_in_generated_schema() -> None:
    schema = ServiceDeploymentInputs.model_json_schema()
    schema_path = (
        Path(__file__).parents[3]
        / "src/apolo_apps_service_deployment/schemas/ServiceDeploymentInputs.json"
    )
    assert json.loads(schema_path.read_text()) == schema
    assert schema["x-routing-inputs"] == ["networking"]


@pytest.mark.usefixtures("mock_get_preset_cpu")
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("preset", {"name": "cpu-medium"}),
        ("image", {"repository": "nginx", "tag": "1.28"}),
        ("autoscaling", {"min_replicas": 2, "max_replicas": 4}),
        ("container", {"env": [{"name": "MODE", "value": "production"}]}),
        ("init_container", [{"image": {"repository": "busybox", "tag": "1.36"}}]),
        (
            "config_map",
            {
                "mount_path": {"path": "/config"},
                "data": [{"key": "mode", "value": "production"}],
            },
        ),
        (
            "storage_mounts",
            {
                "mounts": [
                    {
                        "storage_uri": {
                            "path": "storage://test-cluster/test-org/test-project/data"
                        },
                        "mount_path": {"path": "/data"},
                    }
                ]
            },
        ),
        (
            "health_checks",
            {"readiness": {"health_check_config": {"type": "HTTP", "port": 8080}}},
        ),
    ],
)
async def test_workload_changes_preserve_service_and_ingress(
    setup_clients: Client, field: str, value: object
) -> None:
    assert field not in ServiceDeploymentInputs.model_json_schema()["x-routing-inputs"]
    processor = ServiceDeploymentInputsProcessor(client=setup_clients)
    inputs: dict[str, object] = {
        "preset": {"name": "cpu-small"},
        "image": {"repository": "nginx", "tag": "1.27"},
    }
    values = []
    for configuration in (inputs, {**inputs, field: value}):
        values.append(
            await processor.gen_extra_values(
                input_=ServiceDeploymentInputs.model_validate(configuration),
                app_name="service-app",
                namespace=DEFAULT_NAMESPACE,
                app_secrets_name=APP_SECRETS_NAME,
                app_id=APP_ID,
            )
        )
    assert values[0]["service"] == values[1]["service"]
    assert values[0]["ingress"] == values[1]["ingress"]


async def test_service_deployment_values_generation_with_init_container(
    setup_clients, mock_get_preset_cpu
):
    processor = ServiceDeploymentInputsProcessor(client=setup_clients)
    # noinspection PyArgumentList
    helm_params = await processor.gen_extra_values(
        input_=ServiceDeploymentInputs(
            preset=Preset(name="cpu-small"),
            image=ContainerImage(repository="nginx", tag="1.27"),
            init_container=[
                InitContainer(
                    image=ContainerImage(repository="busybox", tag="1.36"),
                    command=["sh", "-c"],
                    args=["echo init && sleep 1"],
                )
            ],
        ),
        app_name="service-app",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    assert "initContainers" in helm_params
    assert helm_params["initContainers"] == [
        {
            "name": "init-container-1",
            "image": "busybox:1.36",
            "command": ["sh", "-c"],
            "args": ["echo init && sleep 1"],
            "env": [],
            "imagePullPolicy": "IfNotPresent",
        }
    ]


async def test_service_deployment_values_generation_without_init_container(
    setup_clients, mock_get_preset_cpu
):
    processor = ServiceDeploymentInputsProcessor(client=setup_clients)
    # noinspection PyArgumentList
    helm_params = await processor.gen_extra_values(
        input_=ServiceDeploymentInputs(
            preset=Preset(name="cpu-small"),
            image=ContainerImage(repository="nginx", tag="1.27"),
        ),
        app_name="service-app",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    assert "initContainers" not in helm_params


async def test_service_deployment_values_generation_with_multiple_init_containers(
    setup_clients, mock_get_preset_cpu
):
    processor = ServiceDeploymentInputsProcessor(client=setup_clients)
    # noinspection PyArgumentList
    helm_params = await processor.gen_extra_values(
        input_=ServiceDeploymentInputs(
            preset=Preset(name="cpu-small"),
            image=ContainerImage(repository="nginx", tag="1.27"),
            init_container=[
                InitContainer(
                    image=ContainerImage(repository="busybox", tag="1.36"),
                    command=["sh", "-c"],
                    args=["echo init-1"],
                ),
                InitContainer(
                    image=ContainerImage(repository="alpine", tag="3.20"),
                    command=["sh", "-c"],
                    args=["echo init-2"],
                ),
            ],
        ),
        app_name="service-app",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    assert "initContainers" in helm_params
    assert helm_params["initContainers"] == [
        {
            "name": "init-container-1",
            "image": "busybox:1.36",
            "command": ["sh", "-c"],
            "args": ["echo init-1"],
            "env": [],
            "imagePullPolicy": "IfNotPresent",
        },
        {
            "name": "init-container-2",
            "image": "alpine:3.20",
            "command": ["sh", "-c"],
            "args": ["echo init-2"],
            "env": [],
            "imagePullPolicy": "IfNotPresent",
        },
    ]


@pytest.mark.usefixtures("_mock_get_preset_gpu_np")
async def test_service_deployment_values_generation_with_gpu_preset(setup_clients):
    processor = ServiceDeploymentInputsProcessor(client=setup_clients)
    # noinspection PyArgumentList
    helm_params = await processor.gen_extra_values(
        input_=ServiceDeploymentInputs(
            preset=Preset(name="cpu-small-gpu-np"),
            image=ContainerImage(repository="nginx", tag="1.27"),
        ),
        app_name="service-app",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    assert helm_params == {
        "image": {"repository": "nginx", "tag": "1.27", "pullPolicy": "IfNotPresent"},
        "preset_name": "cpu-small-gpu-np",
        "resources": {
            "requests": {"cpu": "2000.0m", "memory": "76294M"},
            "limits": {"cpu": "2000.0m", "memory": "76294M"},
        },
        "tolerations": [
            {
                "effect": "NoSchedule",
                "key": "platform.neuromation.io/job",
                "operator": "Exists",
            },
            {
                "effect": "NoExecute",
                "key": "node.kubernetes.io/not-ready",
                "operator": "Exists",
                "tolerationSeconds": 300,
            },
            {
                "effect": "NoExecute",
                "key": "node.kubernetes.io/unreachable",
                "operator": "Exists",
                "tolerationSeconds": 300,
            },
            {"effect": "NoSchedule", "key": "nvidia.com/gpu", "operator": "Exists"},
        ],
        "affinity": {
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [
                        {
                            "matchExpressions": [
                                {
                                    "key": "platform.neuromation.io/nodepool",
                                    "operator": "In",
                                    "values": ["cpu_pool", "gpu_pool"],
                                }
                            ]
                        }
                    ]
                }
            }
        },
        "podLabels": {
            "platform.apolo.us/component": "app",
            "platform.apolo.us/preset": "cpu-small-gpu-np",
        },
        "ingress": {
            "enabled": True,
            "className": "traefik",
            "hosts": [
                {
                    "host": "custom-deployment--b1aeaf654526474ba22480d00e5b0109.apps.some.org.neu.ro",  # noqa: E501
                    "paths": [{"path": "/", "pathType": "Prefix", "portName": "http"}],
                }
            ],
            "annotations": {
                "traefik.ingress.kubernetes.io/router.middlewares": "platform-platform-control-plane-ingress-auth@kubernetescrd"  # noqa: E501
            },
            "grpc": {"enabled": False},
        },
        "apolo_app_id": "b1aeaf654526474ba22480d00e5b0109",
        "service": {"enabled": True, "ports": [{"name": "http", "containerPort": 80}]},
    }
