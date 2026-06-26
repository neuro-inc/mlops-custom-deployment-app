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

from apolo_app_types.protocols.common import (
    ContainerImage,
    InitContainer,
    Preset,
)


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
