from pydantic import BaseModel, ConfigDict, Field

from apolo_app_types import OptionalSecret
from apolo_app_types.protocols.common import (
    AppInputs,
    IngressHttp,
    Preset,
    SchemaExtraMetadata,
)
from apolo_app_types.protocols.fooocus import FooocusAppOutputs


class FooocusSpecificAppInputs(BaseModel):
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra=SchemaExtraMetadata(
            title="Fooocus App",
            description="Fooocus App configuration.",
        ).as_json_schema_extra(),
    )

    huggingface_token_secret: OptionalSecret = Field(  # noqa: N815
        default=None,
        json_schema_extra=SchemaExtraMetadata(
            title="Hugging Face Token",
            description="Provide the Hugging Face API token"
            " for model access and integration.",
        ).as_json_schema_extra(),
    )


class FooocusAppInputs(AppInputs):
    preset: Preset
    fooocus_specific: FooocusSpecificAppInputs
    ingress_http: IngressHttp


__all__ = ["FooocusAppInputs", "FooocusAppOutputs", "FooocusSpecificAppInputs"]
