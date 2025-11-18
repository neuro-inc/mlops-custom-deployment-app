from typing import Literal

from pydantic import ConfigDict, Field

from apolo_app_types.protocols.common import (
    AbstractAppFieldType,
    ApoloFilesPath,
    AppInputs,
    IngressHttp,
    Preset,
    SchemaExtraMetadata,
)
from apolo_app_types.protocols.mlflow import (
    # apart from it, this definition might still be in shared repo,
    # since it's used by other apps
    MLFlowAppOutputs,  # noqa: F401
)
from apolo_app_types.protocols.postgres import CrunchyPostgresUserCredentials


class MLFlowMetadataPostgres(AbstractAppFieldType):
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra=SchemaExtraMetadata(
            title="Postgres",
            description="Use PostgreSQL server as metadata storage for MLFlow.",
        ).as_json_schema_extra(),
    )

    storage_type: Literal["postgres"] = Field(
        default="postgres",
        json_schema_extra=SchemaExtraMetadata(
            title="Storage Type",
            description="Storage type for MLFlow metadata.",
        ).as_json_schema_extra(),
    )
    postgres_credentials: CrunchyPostgresUserCredentials


class MLFlowMetadataSQLite(AbstractAppFieldType):
    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra=SchemaExtraMetadata(
            title="SQLite",
            description="Use SQLite on a dedicated block "
            "device as metadata store for MLFlow.",
        ).as_json_schema_extra(),
    )

    storage_type: Literal["sqlite"] = Field(
        default="sqlite",
        json_schema_extra=SchemaExtraMetadata(
            title="Storage Type",
            description="Storage type for MLFlow metadata.",
        ).as_json_schema_extra(),
    )


MLFlowMetaStorage = MLFlowMetadataSQLite | MLFlowMetadataPostgres


class MLFlowAppInputs(AppInputs):
    """
    The overall MLFlow app config, referencing:
      - 'preset' for CPU/GPU resources
      - 'ingress' for external URL
      - 'metadata_storage' for MLFlow settings
      - 'artifact_store' for artifacts location
    """

    model_config = ConfigDict(
        protected_namespaces=(),
        json_schema_extra=SchemaExtraMetadata(
            title="MLFlow Inputs",
            description="Configuration for the MLFlow application.",
        ).as_json_schema_extra(),
    )

    preset: Preset
    ingress_http: IngressHttp
    metadata_storage: MLFlowMetaStorage

    artifact_store: ApoloFilesPath = Field(
        default=ApoloFilesPath(path="storage:mlflow-artifacts"),
        json_schema_extra=SchemaExtraMetadata(
            title="Artifact Store",
            description=(
                "Use Apolo Files to store your MLFlow "
                "artifacts (model binaries, dependency files, etc). "
                "Example absolute path: 'storage://cluster/myorg/"
                "proj/mlflow-artifacts' "
                "or relative path: 'storage:mlflow-artifacts'."
            ),
        ).as_json_schema_extra(),
    )
