from pydantic import Field

from apolo_app_types.protocols.common import (
    AppInputs,
    AppOutputs,
    IngressHttp,
    Preset,
)
from apolo_app_types.protocols.common.schema_extra import (
    SchemaExtraMetadata,
    SchemaMetaType,
)


class FooocusAppInputs(AppInputs):
    preset: Preset = Field(
        ...,
        json_schema_extra=SchemaExtraMetadata(
            title="Fooocus preset",
            description="Select the resource preset used for the "
            "Fooocus instance. "
            "Minimal resources: 4 CPU cores, 8 GiB memory, "
            "1 GPU with 4 GiB memory.",
            meta_type=SchemaMetaType.INLINE,
            logo_url=None,
            is_advanced_field=False,
            is_configurable=True,
        ).as_json_schema_extra(),
    )
    ingress_http: IngressHttp


class FooocusAppOutputs(AppOutputs):
    pass


__all__ = ["FooocusAppInputs", "FooocusAppOutputs"]
