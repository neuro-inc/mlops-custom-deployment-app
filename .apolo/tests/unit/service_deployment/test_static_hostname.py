import pytest
from apolo_apps_service_deployment.types import (
    ServiceDeploymentNetworking,
    ServiceDeploymentOutputs,
)
from pydantic import ValidationError

from apolo_app_types.protocols.custom_deployment import NetworkingConfig


@pytest.mark.parametrize(
    "label", ["", "Upper", "a.b", "*", "-api", "api-", "a" * 64, "a\n", "é"]
)
def test_invalid_static_hostname(label):
    with pytest.raises(ValidationError):
        ServiceDeploymentNetworking(ingress_http={"static_hostname": label})


def test_static_hostname_requires_service():
    with pytest.raises(ValidationError):
        ServiceDeploymentNetworking(
            service_enabled=False, ingress_http={"static_hostname": "api"}
        )


def test_optional_field_and_legacy_outputs():
    assert ServiceDeploymentNetworking().ingress_http.static_hostname is None
    assert ServiceDeploymentOutputs().static_url is None
    assert (
        "static_hostname"
        not in NetworkingConfig.model_json_schema()["$defs"]["IngressHttp"][
            "properties"
        ]
    )
