from typing import Self

from pydantic import Field, model_validator

from apolo_app_types.protocols.common import IngressHttp
from apolo_app_types.protocols.common.schema_extra import (
    SchemaExtraMetadata,
)
from apolo_app_types.protocols.custom_deployment import (
    CustomDeploymentInputs,
    CustomDeploymentOutputs,
    NetworkingConfig,
    Preset,
)


class ServiceDeploymentIngress(IngressHttp):
    static_hostname: str | None = Field(
        default=None,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$",
        json_schema_extra=SchemaExtraMetadata(
            title="Static hostname",
            description="Optional globally reserved name, such as my-api. "
            "The platform adds its Apps domain and retains ownership "
            "across deployments.",
        ).as_json_schema_extra(),
    )


class ServiceDeploymentNetworking(NetworkingConfig):
    ingress_http: ServiceDeploymentIngress | None = Field(
        default_factory=ServiceDeploymentIngress,
    )

    @model_validator(mode="after")
    def validate_static_service(self) -> Self:
        if (
            self.ingress_http
            and self.ingress_http.static_hostname
            and not self.service_enabled
        ):
            message = "Static hostname requires an enabled Service"
            raise ValueError(message)
        return self


class ServiceDeploymentInputs(CustomDeploymentInputs):
    networking: ServiceDeploymentNetworking = Field(
        default_factory=ServiceDeploymentNetworking,
    )
    preset: Preset = Field(
        ...,
        json_schema_extra=SchemaExtraMetadata(
            title="Service Deployment preset",
            description="Select the resource preset used for the instance. "
            "Minimal resources depends on your application needs, "
            "but a good starting point is 0.5 CPU cores and 512 MiB memory.",
        ).as_json_schema_extra(),
    )


class ServiceDeploymentOutputs(CustomDeploymentOutputs):
    static_url: str | None = Field(
        default=None,
        description=(
            "Verified global URL, populated by the Apps API after routing is ready."
        ),
    )
