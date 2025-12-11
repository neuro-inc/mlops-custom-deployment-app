import json

import pytest
from apolo_app_types_fixtures.constants import (
    APP_ID,
    APP_SECRETS_NAME,
    DEFAULT_CLUSTER_NAME,
    DEFAULT_NAMESPACE,
    DEFAULT_ORG_NAME,
    DEFAULT_PROJECT_NAME,
)
from apolo_apps_jupyter.inputs_processor import JupyterInputsProcessor
from apolo_apps_jupyter.types import (
    _JUPYTER_DEFAULTS,
    CustomImage,
    JupyterAppInputs,
    JupyterSpecificAppInputs,
)

from apolo_app_types import Container, ContainerImage
from apolo_app_types.protocols.common import Preset


@pytest.mark.asyncio
async def test_jupyter_values_generation(setup_clients):
    input_data = JupyterAppInputs(
        preset=Preset(name="cpu-small"),
        jupyter_specific=JupyterSpecificAppInputs(),
    )

    # Create the processor instance with the client
    processor = JupyterInputsProcessor(client=setup_clients)

    # Call gen_extra_values directly
    helm_params = await processor.gen_extra_values(
        input_=input_data,
        app_name="jupyter-app",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    assert helm_params["image"] == {
        "repository": "ghcr.io/neuro-inc/base",
        "tag": "v25.3.0-runtime",
        "pullPolicy": "IfNotPresent",
    }

    assert helm_params["service"] == {
        "enabled": True,
        "ports": [{"name": "http", "containerPort": 8888}],
    }

    assert "podAnnotations" in helm_params
    annotations = helm_params["podAnnotations"]
    assert "platform.apolo.us/inject-storage" in annotations

    storage_json = annotations["platform.apolo.us/inject-storage"]
    parsed_storage = json.loads(storage_json)

    assert (
        parsed_storage[0]["storage_uri"]
        == f"storage://{DEFAULT_CLUSTER_NAME}/{DEFAULT_ORG_NAME}/{DEFAULT_PROJECT_NAME}/"
        f".apps/jupyter/jupyter-app/code"
    )
    assert parsed_storage[0]["mount_path"] == "/root/notebooks"
    assert parsed_storage[0]["mount_mode"] == "rw"

    pod_labels = helm_params.get("podLabels", {})
    assert pod_labels.get("platform.apolo.us/inject-storage") == "true"


@pytest.mark.asyncio
async def test_jupyter_custom_image_values_generation(setup_clients):
    input_data = JupyterAppInputs(
        preset=Preset(name="cpu-small"),
        jupyter_specific=JupyterSpecificAppInputs(
            container_settings=CustomImage(
                container_image=ContainerImage(
                    repository="image-name",
                    tag="latest",
                ),
                container_config=Container(
                    command=["start-notebook.sh"],
                    args=["--NotebookApp.token=''"],
                ),
            ),
        ),
    )

    # Create the processor instance with the client
    processor = JupyterInputsProcessor(client=setup_clients)

    # Call gen_extra_values directly
    helm_params = await processor.gen_extra_values(
        input_=input_data,
        app_name="jupyter-app",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    assert helm_params["image"] == {
        "repository": "image-name",
        "tag": "latest",
        "pullPolicy": "IfNotPresent",
    }
    assert helm_params["container"] == {
        "command": ["start-notebook.sh"],
        "args": ["--NotebookApp.token=''"],
        "env": [],
    }

    assert helm_params["service"] == {
        "enabled": True,
        "ports": [{"name": "http", "containerPort": 8888}],
    }

    assert "podAnnotations" in helm_params
    annotations = helm_params["podAnnotations"]
    assert "platform.apolo.us/inject-storage" in annotations

    storage_json = annotations["platform.apolo.us/inject-storage"]
    parsed_storage = json.loads(storage_json)

    assert (
        parsed_storage[0]["storage_uri"]
        == f"storage://{DEFAULT_CLUSTER_NAME}/{DEFAULT_ORG_NAME}/{DEFAULT_PROJECT_NAME}/"
        f".apps/jupyter/jupyter-app/code"
    )
    assert parsed_storage[0]["mount_path"] == _JUPYTER_DEFAULTS["mount"]
    assert parsed_storage[0]["mount_mode"] == "rw"

    pod_labels = helm_params.get("podLabels", {})
    assert pod_labels.get("platform.apolo.us/inject-storage") == "true"
