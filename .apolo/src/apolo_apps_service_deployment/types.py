from pydantic import Field

from apolo_app_types.protocols.common.schema_extra import (
    SchemaExtraMetadata,
)
from apolo_app_types.protocols.custom_deployment import (
    CustomDeploymentInputs,
    CustomDeploymentOutputs,
    Preset,
)


class ServiceDeploymentInputs(CustomDeploymentInputs):
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
