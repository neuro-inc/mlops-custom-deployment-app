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
            "name": "init-container",
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
