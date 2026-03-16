from pydantic import Field

from apolo_app_types.protocols.common import (
    AppInputs,
    AppOutputs,
    IngressHttp,
    Preset,
    SchemaExtraMetadata,
)


class FooocusAppInputs(AppInputs):
    preset: Preset = Field(
        ...,
        json_schema_extra=SchemaExtraMetadata(
            title="Foocus preset",
            description="Select the resource preset used for the "
            "Foocus instance. "
            "Minimal resources: 4 CPU cores, 8 GiB memory, 1 GPU with 4 GiB memory.",
        ).as_json_schema_extra(),
    )
    ingress_http: IngressHttp


class FooocusAppOutputs(AppOutputs):
    pass


__all__ = ["FooocusAppInputs", "FooocusAppOutputs"]
