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
from apolo_apps_fooocus.inputs_processor import FooocusInputsProcessor
from apolo_apps_fooocus.types import (
    FooocusAppInputs,
)

from apolo_app_types.protocols.common import IngressHttp, Preset


@pytest.mark.asyncio
async def test_fooocus_values_generation(setup_clients):
    input_data = FooocusAppInputs(
        preset=Preset(name="cpu-small"),
        ingress_http=IngressHttp(
            clusterName="default",
        ),
    )

    # Create the processor instance with the client
    processor = FooocusInputsProcessor(client=setup_clients)

    # Call gen_extra_values directly
    helm_params = await processor.gen_extra_values(
        input_=input_data,
        app_name="fooocus-app",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )

    assert helm_params["image"] == {
        "repository": "ghcr.io/neuro-inc/fooocus",
        "tag": "latest",
        "pullPolicy": "IfNotPresent",
    }

    assert helm_params["service"] == {
        "enabled": True,
        "ports": [{"name": "http", "containerPort": 7865}],
    }

    assert "podAnnotations" in helm_params
    annotations = helm_params["podAnnotations"]
    assert "platform.apolo.us/inject-storage" in annotations

    storage_json = annotations["platform.apolo.us/inject-storage"]
    parsed_storage = json.loads(storage_json)
    assert len(parsed_storage) == 2

    assert (
        parsed_storage[0]["storage_uri"]
        == f"storage://{DEFAULT_CLUSTER_NAME}/{DEFAULT_ORG_NAME}/{DEFAULT_PROJECT_NAME}/"
        f".apps/fooocus/fooocus-app/data"
    )
    assert parsed_storage[0]["mount_path"] == "/content/data"
    assert parsed_storage[0]["mount_mode"] == "rw"

    assert parsed_storage[1]["storage_uri"] == (
        f"storage://{DEFAULT_CLUSTER_NAME}/{DEFAULT_ORG_NAME}/{DEFAULT_PROJECT_NAME}/"
        f".apps/fooocus/fooocus-app/app/outputs"
    )
    assert parsed_storage[1]["mount_path"] == "/content/app/outputs"
    assert parsed_storage[1]["mount_mode"] == "rw"

    pod_labels = helm_params.get("podLabels", {})
    assert pod_labels.get("platform.apolo.us/inject-storage") == "true"

    # Verify Fooocus gets ONLY auth middleware (no strip headers)
    assert (
        helm_params["ingress"]["annotations"][
            "traefik.ingress.kubernetes.io/router.middlewares"
        ]
        == "platform-platform-control-plane-ingress-auth@kubernetescrd"
    )
