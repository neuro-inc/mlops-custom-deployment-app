from decimal import Decimal

import pytest
from apolo_apps_triton.types import TritonAppInputs
from apolo_sdk import Preset

from apolo_app_types.protocols.common import (
    ApoloFilesPath,
    ContainerImage,
    Preset as PresetInput,
)
from apolo_app_types.protocols.triton import TritonModelRepository


MEBIBYTE = 1 << 20
PRESETS = {
    "cpu-small": Preset(
        cpu=1.0,
        memory=10**9,
        credits_per_hour=Decimal("0.1"),
        available_resource_pool_names=("cpu_pool",),
    ),
    "cpu-micro": Preset(
        cpu=0.1,
        memory=100 * MEBIBYTE,
        credits_per_hour=Decimal("0.01"),
        available_resource_pool_names=("cpu_pool",),
    ),
    "cpu-999": Preset(
        cpu=1.0,
        memory=10**9 - 1,
        credits_per_hour=Decimal("0.1"),
        available_resource_pool_names=("cpu_pool",),
    ),
    "cpu-large": Preset(
        cpu=4.0,
        memory=16384 * MEBIBYTE,
        credits_per_hour=Decimal("0.4"),
        available_resource_pool_names=("cpu_pool",),
    ),
}
NAMESPACE = "platform--org--project--0a1b2c3d"
IMAGE = ContainerImage(repository="nvcr.io/nvidia/tritonserver", tag="26.10-py3")


@pytest.fixture
def presets_available():
    return PRESETS


@pytest.fixture
def minimal_inputs():
    return TritonAppInputs(
        preset=PresetInput(name="cpu-small"),
        image=IMAGE,
        model_repository=TritonModelRepository(
            files_path=ApoloFilesPath(path="storage:triton/models")
        ),
    )


@pytest.fixture(autouse=True)
def _namespace(monkeypatch):
    monkeypatch.setenv("APOLO_APP_NAMESPACE", NAMESPACE)
