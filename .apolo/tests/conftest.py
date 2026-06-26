from decimal import Decimal

import pytest
from apolo_sdk import Preset


pytest_plugins = [
    "apolo_app_types_fixtures.apolo_clients",
    "apolo_app_types_fixtures.constants",
]


TEST_PRESETS_WITH_GPU_NP_CLUSTER = {
    "cpu-small-gpu-np": Preset(
        cpu=2.0,
        memory=8e10,
        credits_per_hour=Decimal("0.05"),
        available_resource_pool_names=("cpu_pool", "gpu_pool"),
    ),
}


@pytest.fixture
def _mock_get_preset_gpu_np(setup_clients):
    from unittest.mock import AsyncMock

    setup_clients.config.presets = TEST_PRESETS_WITH_GPU_NP_CLUSTER
    setup_clients.jobs.get_capacity = AsyncMock(
        return_value={name: 10 for name in TEST_PRESETS_WITH_GPU_NP_CLUSTER}
    )
