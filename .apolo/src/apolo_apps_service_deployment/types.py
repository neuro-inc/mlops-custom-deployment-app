from pydantic import ConfigDict, Field, JsonValue

from apolo_app_types.protocols.common.schema_extra import (
    SchemaExtraMetadata,
)
from apolo_app_types.protocols.custom_deployment import (
    CustomDeploymentInputs,
    CustomDeploymentOutputs,
    Preset,
)


_custom_deployment_schema_extra = CustomDeploymentInputs.model_config.get(
    "json_schema_extra"
)
if not isinstance(_custom_deployment_schema_extra, dict):
    message = "Custom Deployment schema metadata must be a dictionary"
    raise TypeError(message)


_service_deployment_schema_extra: dict[str, JsonValue] = {
    **_custom_deployment_schema_extra,
    "x-routing-inputs": ["networking"],
}


class ServiceDeploymentInputs(CustomDeploymentInputs):
    model_config = ConfigDict(json_schema_extra=_service_deployment_schema_extra)
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
    pass
