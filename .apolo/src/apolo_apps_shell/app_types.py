from pydantic import Field

from apolo_app_types.protocols.common import (
    AppInputs,
    AppOutputs,
    BasicNetworkingConfig,
    Preset,
    SchemaExtraMetadata,
)


class ShellAppInputs(AppInputs):
    preset: Preset = Field(
        ...,
        json_schema_extra=SchemaExtraMetadata(
            title="Shell preset",
            description="Select the resource preset used for the "
            "Shell instance. "
            "Minimal resources: 0.1 CPU cores, 128 MiB memory.",
        ).as_json_schema_extra(),
    )
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
