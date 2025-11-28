from pydantic import BaseModel, ConfigDict, Field

from apolo_app_types import (
    AppInputs,
    CrunchyPostgresUserCredentials,
)
from apolo_app_types.protocols.common import (
    IngressHttp,
    Preset,
    SchemaExtraMetadata,
)
from apolo_app_types.protocols.common.openai_compat import (
    OpenAICompatChatAPI,
    OpenAICompatEmbeddingsAPI,
)


class PrivateGptSpecific(BaseModel):
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra=SchemaExtraMetadata(
            title="PrivateGPT Specific",
            description="Configure PrivateGPT additional parameters.",
        ).as_json_schema_extra(),
    )
    llm_temperature: float = Field(
        default=0.1,
        json_schema_extra=SchemaExtraMetadata(
            title="LLM Temperature",
            description="Configure temperature for LLM inference.",
        ).as_json_schema_extra(),
    )
    embeddings_dimension: int = Field(
        default=768,
        gt=0,
        json_schema_extra=SchemaExtraMetadata(
            title="Embeddings Dimension",
            description="Configure dimension of embeddings."
            "The number can be found on the Hugging Face model card "
            "or model configuration file.",
        ).as_json_schema_extra(),
    )
    llm_max_new_tokens: int = Field(
        default=5000,
        gt=0,
        json_schema_extra=SchemaExtraMetadata(
            title="LLM Max New Tokens",
            description="Configure maximum number of new tokens "
            "(limited by GPU memory and model size).",
        ).as_json_schema_extra(),
    )
    llm_context_window: int = Field(
        default=8192,
        gt=0,
        json_schema_extra=SchemaExtraMetadata(
            title="LLM Context Window",
            description="Configure context window for LLM inference "
            "(defined by model architecture).",
        ).as_json_schema_extra(),
    )
    llm_tokenizer_name: str | None = Field(
        default=None,
        json_schema_extra=SchemaExtraMetadata(
            title="LLM Tokenizer Name",
            description="Configure tokenizer name for LLM inference.",
        ).as_json_schema_extra(),
    )


class PrivateGPTAppInputs(AppInputs):
    preset: Preset
    ingress_http: IngressHttp
    pgvector_user: CrunchyPostgresUserCredentials
    embeddings_api: OpenAICompatEmbeddingsAPI
    llm_chat_api: OpenAICompatChatAPI
    private_gpt_specific: PrivateGptSpecific = Field(
        default_factory=lambda: PrivateGptSpecific(),
    )
