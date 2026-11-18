from pydantic import Field

from apolo_app_types.protocols.common import (
    AppInputs,
    AppOutputs,
    ContainerImage,
    Env,
    IngressGrpc,
    IngressHttp,
    Preset,
    SchemaExtraMetadata,
    SchemaMetaType,
    ServiceAPI,
)
from apolo_app_types.protocols.common.hugging_face import (
    HF_TOKEN_SCHEMA_EXTRA,
    HuggingFaceCache,
    HuggingFaceToken,
)
from apolo_app_types.protocols.triton import (
    TritonModelRepository,
    TritonServerGRPCEndpoint,
    TritonServerHttpEndpoint,
)


class TritonAppInputs(AppInputs):
    preset: Preset
    image: ContainerImage = Field(
        default=ContainerImage(
            repository="nvcr.io/nvidia/tritonserver", tag="26.10-py3"
        ),
        json_schema_extra=SchemaExtraMetadata(
            title="Triton Server Image",
            description="Triton Inference Server image with a tag (e.g. "
            "26.10-py3) or a sha256 digest. The server is started as "
            "`tritonserver --model-repository=/models <extra args>` through the "
            "image entrypoint.",
        ).as_json_schema_extra(),
    )
    model_repository: TritonModelRepository
    ingress_http: IngressHttp | None = Field(
        default=None,
        json_schema_extra=SchemaExtraMetadata(
            title="Public HTTP Endpoint",
            description="Expose the Triton HTTP/REST API (inference and model "
            "management) over HTTPS. Platform authentication is on by default.",
        ).as_json_schema_extra(),
    )
    ingress_grpc: IngressGrpc | None = Field(
        default=None,
        json_schema_extra=SchemaExtraMetadata(
            title="Public gRPC Endpoint",
            description="Expose the Triton gRPC API over TLS on port 443. "
            "Platform authentication is on by default: send "
            "`authorization: Bearer <token>` as call metadata.",
        ).as_json_schema_extra(),
    )
    server_extra_args: list[str] = Field(
        default_factory=list,
        json_schema_extra=SchemaExtraMetadata(
            title="Server Extra Arguments",
            description="Arguments appended to the tritonserver command, e.g. "
            "--log-verbose=1 or --exit-on-error=false --strict-readiness=false. "
            "Ports, addresses and gRPC TLS are managed by the app.",
            is_advanced_field=True,
        ).as_json_schema_extra(),
    )
    hf_cache: HuggingFaceCache | None = Field(
        default=None,
        json_schema_extra=SchemaExtraMetadata(
            title="Hugging Face Cache",
            description="Mounted at /root/.cache/huggingface; HF_HOME points there.",
            meta_type=SchemaMetaType.INTEGRATION,
            is_advanced_field=True,
        ).as_json_schema_extra(),
    )
    hf_token: HuggingFaceToken | None = Field(
        default=None,
        json_schema_extra=HF_TOKEN_SCHEMA_EXTRA.model_copy(
            update={
                "is_advanced_field": True,
                "description": "Passed to the server as HF_TOKEN.",
            }
        ).as_json_schema_extra(),
    )
    extra_env_vars: list[Env] = Field(
        default_factory=list,
        json_schema_extra=SchemaExtraMetadata(
            title="Extra Environment Variables",
            description="Added to the server container; they override variables "
            "set by the app, HF_HOME and HF_TOKEN included.",
            is_advanced_field=True,
        ).as_json_schema_extra(),
    )


class TritonAppOutputs(AppOutputs):
    http_endpoint: ServiceAPI[TritonServerHttpEndpoint] | None = Field(
        default=None,
        json_schema_extra=SchemaExtraMetadata(
            title="Triton Server HTTP Endpoint",
            description="KServe v2 HTTP/REST API, container port 8000.",
            meta_type=SchemaMetaType.INTEGRATION,
        ).as_json_schema_extra(),
    )
    grpc_endpoint: ServiceAPI[TritonServerGRPCEndpoint] | None = Field(
        default=None,
        json_schema_extra=SchemaExtraMetadata(
            title="Triton Server gRPC Endpoint",
            description="KServe v2 gRPC API, container port 8001.",
            meta_type=SchemaMetaType.INTEGRATION,
        ).as_json_schema_extra(),
    )
