import enum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apolo_app_types import (
    AppInputs,
)
from apolo_app_types.protocols.common import (
    Preset,
    SchemaExtraMetadata,
    SchemaMetaType,
)
from apolo_app_types.protocols.common.abc_ import AbstractAppFieldType
from apolo_app_types.protocols.common.ingress import (
    BasicNetworkingConfig,
)
from apolo_app_types.protocols.common.k8s import Env
from apolo_app_types.protocols.common.openai_compat import (
    OpenAICompatAPI,
    OpenAICompatCapability,
    OpenAICompatChatAPI,
    OpenAICompatEmbeddingsAPI,
)
from apolo_app_types.protocols.openwebui import (
    OpenWebUIAppOutputs,
)
from apolo_app_types.protocols.postgres import (
    CrunchyPostgresUserCredentials,
)


class DBTypes(enum.StrEnum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"


class OpenWebUISpecific(BaseModel):
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra=SchemaExtraMetadata(
            title="OpenWebUI Specific",
            description="Configure OpenWebUI additional parameters.",
        ).as_json_schema_extra(),
    )
    env: list[Env] = Field(
        default_factory=list,
        json_schema_extra=SchemaExtraMetadata(
            title="Environment Variables",
            description="List of environment variables to set in"
            " the OpenWebUI application.",
        ).as_json_schema_extra(),
    )


class SQLiteDatabase(AbstractAppFieldType):
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra=SchemaExtraMetadata(
            title="SQLite Database",
            description="Use a local SQLite database for OpenWebUI.",
        ).as_json_schema_extra(),
    )
    # No additional fields needed for local SQLite database
    database_type: Literal[DBTypes.SQLITE] = Field(default=DBTypes.SQLITE)


class PostgresDatabase(AbstractAppFieldType):
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra=SchemaExtraMetadata(
            title="Postgres Database",
            description="Use a Postgres database for OpenWebUI.",
        ).as_json_schema_extra(),
    )
    # Use Crunchy Postgres credentials for the database
    database_type: Literal[DBTypes.POSTGRES] = Field(default=DBTypes.POSTGRES)
    credentials: CrunchyPostgresUserCredentials


class DataBaseConfig(AbstractAppFieldType):
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra=SchemaExtraMetadata(
            title="Database Configuration",
            description="Configure the database for OpenWebUI.",
        ).as_json_schema_extra(),
    )
    database: SQLiteDatabase | PostgresDatabase = Field(
        default_factory=lambda: SQLiteDatabase(),
        json_schema_extra=SchemaExtraMetadata(
            title="Database Configuration",
            description="Configure the database for OpenWebUI. "
            "Choose between local SQLite or Postgres.",
        ).as_json_schema_extra(),
    )


class OpenWebUIAppInputs(AppInputs):
    preset: Preset = Field(
        ...,
        json_schema_extra=SchemaExtraMetadata(
            title="OpenWebUI preset",
            description="Select the resource preset used for the "
            "OpenWebUI instance. "
            "Minimal resources: 0.5 CPU cores, 512 MiB memory.",
        ).as_json_schema_extra(),
    )
    networking_config: BasicNetworkingConfig = Field(
        ...,
        json_schema_extra=SchemaExtraMetadata(
            title="Networking Configuration",
            description="Networking configuration for the OpenWebUI application.",
            is_advanced_field=True,
        ).as_json_schema_extra(),
    )
    database_config: DataBaseConfig
    openai_api: OpenAICompatAPI | None = Field(
        default=None,
        json_schema_extra=SchemaExtraMetadata(
            title="Model Gateway API",
            description="OpenAI compatible API of a model gateway such as Bifrost, "
            "used instead of an LLM Chat API. Chat offers every model the gateway "
            "lists, including embeddings, speech and transcription models; limit "
            "the list with Model IDs in Admin Settings > Connections. Documents "
            "are embedded only with the Embeddings API, which can be an "
            "embeddings API of the same gateway. OpenWebUI keeps the connection "
            "URL and the embedding settings once they are saved in Admin "
            "Settings > Connections or Documents, so an existing installation "
            "switched to a gateway keeps the old values until they are changed "
            "there.",
            meta_type=SchemaMetaType.INTEGRATION,
        ).as_json_schema_extra(),
    )
    embeddings_api: OpenAICompatEmbeddingsAPI
    llm_chat_api: OpenAICompatChatAPI | None = Field(
        default=None,
        json_schema_extra=SchemaExtraMetadata(
            title="LLM Chat API",
            description="Chat API of a single model server. Use it instead of "
            "a model gateway API.",
            meta_type=SchemaMetaType.INTEGRATION,
        ).as_json_schema_extra(),
    )
    openwebui_specific: OpenWebUISpecific = Field(
        default_factory=lambda: OpenWebUISpecific(),
    )

    @model_validator(mode="after")
    def _require_models(self) -> Self:
        if (self.openai_api is None) == (self.llm_chat_api is None):
            msg = "Set either the model gateway API or the LLM chat API"
            raise ValueError(msg)
        if self.openai_api and not (
            self.openai_api.get_model_names(OpenAICompatCapability.CHAT)
            or self.openai_api.model_prefixes
        ):
            msg = "The model gateway API serves no chat model"
            raise ValueError(msg)
        return self


__all__ = [
    "OpenWebUIAppInputs",
    "OpenWebUIAppOutputs",
]
