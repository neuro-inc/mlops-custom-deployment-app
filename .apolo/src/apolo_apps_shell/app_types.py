from apolo_app_types.protocols.common import (
    AppInputs,
    AppOutputs,
    BasicNetworkingConfig,
    Preset,
    SchemaExtraMetadata,
)
from pydantic import Field


class ShellAppInputs(AppInputs):
    preset: Preset
    networking: BasicNetworkingConfig = Field(
        default_factory=BasicNetworkingConfig,
        json_schema_extra=SchemaExtraMetadata(
            title="Networking Settings",
            description="Configure network access, HTTP authentication,"
            " and related connectivity options.",
        ).as_json_schema_extra(),
    )


class ShellAppOutputs(AppOutputs):
    pass
