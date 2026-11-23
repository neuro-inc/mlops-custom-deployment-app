import re
import typing as t
import unicodedata

import apolo_sdk
from yarl import URL

from apolo_app_types.app_types import AppType
from apolo_app_types.helm.apps.base import BaseChartValueProcessor
from apolo_app_types.helm.apps.common import (
    append_apolo_storage_integration_annotations,
    gen_apolo_storage_integration_labels,
    gen_extra_values,
    get_preset,
)
from apolo_app_types.helm.utils.images import (
    get_image_docker_url,
    resolve_image_dockerconfig,
)
from apolo_app_types.protocols.common import (
    ApoloFilesMount,
    ApoloMountMode,
    IngressGrpc,
    IngressHttp,
    MountPath,
    NoAuth,
)
from apolo_app_types.protocols.common.secrets_ import serialize_optional_secret
from apolo_app_types.protocols.common.storage import ApoloFilesPath, ApoloMountModes
from apolo_apps_triton.types import TritonAppInputs


FULLNAME_PREFIX = "triton"
APPLICATION_LABEL = "triton"
MODEL_REPOSITORY_PATH = "/models"
HF_CACHE_PATH = "/root/.cache/huggingface"
MIN_MEMORY_BYTES = 10**9
HTTP_PORT = 8000
GRPC_PORT = 8001
METRICS_PORT = 8002
GRPC_SERVICE_NAME = "grpc"
INGRESS_CLASS_NAME = "traefik"
SERVERS_SCHEME_ANNOTATION = "traefik.ingress.kubernetes.io/service.serversscheme"
CHART_POD_LABELS = frozenset(
    {"platform.apolo.us/component", "platform.apolo.us/preset"}
)
STARTUP_PERIOD_SECONDS = 10
STARTUP_FAILURE_THRESHOLD = 180
PROGRESS_DEADLINE_MARGIN_SECONDS = 300
PROBE_TIMEOUT_SECONDS = 2
MODEL_CONTROL_MODE_FLAG = "--model-control-mode"
EXPLICIT_MODE = "explicit"
RESTRICTION_FLAGS = frozenset({"--http-restricted-api", "--grpc-restricted-protocol"})
HEALTH_API = "health"
VARIABLE_REFERENCE = "$("
VERTEX_AI_ENV_PREFIX = "AIP_"
ENV_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
YAML_SCALAR_ENV_NAMES = frozenset(
    spelling
    for word in ("y", "yes", "n", "no", "true", "false", "on", "off", "null")
    for spelling in (word, word.capitalize(), word.upper())
)
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
STORAGE_PREFIX = "storage:"
FORBIDDEN_FLAGS = frozenset(
    {
        "--http-port",
        "--grpc-port",
        "--metrics-port",
        "--http-address",
        "--grpc-address",
        "--metrics-address",
        "--allow-http",
        "--allow-grpc",
        "--grpc-use-ssl",
        "--grpc-use-ssl-mutual",
        "--grpc-server-cert",
        "--grpc-server-key",
        "--grpc-root-cert",
    }
)
SERVER_FLAGS = frozenset(
    {
        *FORBIDDEN_FLAGS,
        MODEL_CONTROL_MODE_FLAG,
        "--allow-client-shm",
        "--allow-cpu-metrics",
        "--allow-gpu-metrics",
        "--allow-metrics",
        "--allow-sagemaker",
        "--allow-vertex-ai",
        "--backend-config",
        "--backend-directory",
        "--buffer-manager-thread-count",
        "--cache-config",
        "--cache-directory",
        "--cuda-memory-pool-byte-size",
        "--cuda-virtual-address-size",
        "--disable-auto-complete-config",
        "--enable-peer-access",
        "--exit-on-error",
        "--exit-timeout-secs",
        "--grpc-header-forward-pattern",
        "--grpc-http2-max-ping-strikes",
        "--grpc-http2-max-pings-without-data",
        "--grpc-http2-min-recv-ping-interval-without-data",
        "--grpc-infer-allocation-pool-size",
        "--grpc-infer-response-compression-level",
        "--grpc-infer-thread-count",
        "--grpc-keepalive-permit-without-calls",
        "--grpc-keepalive-time",
        "--grpc-keepalive-timeout",
        "--grpc-max-connection-age",
        "--grpc-max-connection-age-grace",
        "--grpc-max-response-pool-size",
        "--grpc-restricted-protocol",
        "--help",
        "--host-policy",
        "--http-header-forward-pattern",
        "--http-max-input-size",
        "--http-restricted-api",
        "--http-thread-count",
        "--id",
        "--load-model",
        "--log-error",
        "--log-file",
        "--log-format",
        "--log-info",
        "--log-verbose",
        "--log-warning",
        "--metrics-config",
        "--metrics-interval-ms",
        "--min-supported-compute-capability",
        "--model-config-name",
        "--model-load-gpu-limit",
        "--model-load-retry-count",
        "--model-load-thread-count",
        "--model-namespacing",
        "--model-repository",
        "--model-store",
        "--pinned-memory-pool-byte-size",
        "--rate-limit",
        "--rate-limit-resource",
        "--repoagent-directory",
        "--repository-poll-secs",
        "--response-cache-byte-size",
        "--reuse-grpc-port",
        "--reuse-http-port",
        "--sagemaker-port",
        "--sagemaker-safe-port-range",
        "--sagemaker-thread-count",
        "--strict-model-config",
        "--strict-readiness",
        "--trace-config",
        "--trace-count",
        "--trace-file",
        "--trace-level",
        "--trace-log-frequency",
        "--trace-rate",
        "--vertex-ai-default-model",
        "--vertex-ai-port",
        "--vertex-ai-thread-count",
    }
)


def get_fullname(app_id: str) -> str:
    return f"{FULLNAME_PREFIX}-{app_id}"


def _escape(value: str) -> str:
    return value.replace("$", "$$")


def _resolve_flag(name: str) -> str | None:
    if name in SERVER_FLAGS:
        return name
    matches = sorted(flag for flag in SERVER_FLAGS if flag.startswith(name))
    if len(matches) > 1:
        msg = (
            f"Server extra argument {name} is ambiguous: "
            f"it may mean {', '.join(matches)}"
        )
        raise ValueError(msg)
    return matches[0] if matches else None


def _parse_server_args(args: list[str]) -> list[tuple[str, str]]:
    parsed = []
    for index, arg in enumerate(args):
        if not arg.startswith("--") or arg == "--":
            continue
        name, separator, value = arg.partition("=")
        flag = _resolve_flag(name)
        if flag is None:
            continue
        if not separator:
            value = args[index + 1] if index + 1 < len(args) else ""
        parsed.append((flag, value))
    return parsed


def _is_open(ingress: IngressHttp | IngressGrpc | None) -> bool:
    return ingress is not None and isinstance(ingress.auth, NoAuth)


def _check_server_args(input_: TritonAppInputs) -> None:
    if any(not arg.strip() for arg in input_.server_extra_args):
        msg = (
            "Server extra arguments must not contain empty items: "
            "tritonserver stops on them"
        )
        raise ValueError(msg)
    if any(VARIABLE_REFERENCE in arg for arg in input_.server_extra_args):
        msg = (
            "Server extra arguments must not contain $(: "
            "variable references are not supported in server arguments"
        )
        raise ValueError(msg)
    parsed = _parse_server_args(input_.server_extra_args)
    forbidden = sorted({flag for flag, _ in parsed if flag in FORBIDDEN_FLAGS})
    if forbidden:
        msg = (
            f"Server extra arguments must not set {', '.join(forbidden)}: "
            "ports, addresses and gRPC TLS are managed by the app"
        )
        raise ValueError(msg)
    restricted = {
        api.strip().lower()
        for flag, value in parsed
        if flag in RESTRICTION_FLAGS
        for api in value.partition(":")[0].split(",")
    }
    if HEALTH_API in restricted:
        msg = (
            "Server extra arguments must not restrict the health API: "
            "the probes of the app call it without the restriction header"
        )
        raise ValueError(msg)
    explicit = any(
        flag == MODEL_CONTROL_MODE_FLAG and value.strip().lower() == EXPLICIT_MODE
        for flag, value in parsed
    )
    if explicit and (_is_open(input_.ingress_http) or _is_open(input_.ingress_grpc)):
        msg = (
            "--model-control-mode=explicit lets callers load and unload models, "
            "so a public endpoint without authentication is not allowed with it"
        )
        raise ValueError(msg)


def _has_control_characters(value: str) -> bool:
    return any(unicodedata.category(char) == "Cc" for char in value)


def _refuse_storage_path(files_path: ApoloFilesPath, title: str) -> t.NoReturn:
    msg = (
        f"{title} {files_path.path!r} must be a plain storage path: "
        "no ':', '?', '#', control characters, user or port"
    )
    raise ValueError(msg)


def _check_storage_path(files_path: ApoloFilesPath, title: str) -> None:
    rest = files_path.path.removeprefix(STORAGE_PREFIX)
    authority, path = "", rest
    if rest.startswith("//"):
        authority, _, path = rest[2:].partition("/")
    if (
        any(char in rest for char in "?#")
        or _has_control_characters(rest)
        or any(char in authority for char in ":@")
        or ":" in path
    ):
        _refuse_storage_path(files_path, title)


def _get_project_path(
    client: apolo_sdk.Client, files_path: ApoloFilesPath, title: str
) -> ApoloFilesPath:
    _check_storage_path(files_path, title)
    uri = URL(files_path.get_absolute_path_model(client).path)
    config = client.config
    project = tuple(part for part in (config.org_name, config.project_name) if part)
    parts = tuple(part for part in uri.path.split("/") if part)
    if _has_control_characters(uri.path) or ":" in uri.path:
        _refuse_storage_path(files_path, title)
    project_root = "/".join((config.cluster_name, *project))
    if (
        uri.host != config.cluster_name
        or parts[: len(project)] != project
        or ".." in parts
    ):
        msg = (
            f"{title} {files_path.path} must be in the project of the app "
            f"(storage://{project_root})"
        )
        raise ValueError(msg)
    if len(parts) == len(project):
        msg = (
            f"{title} {files_path.path} must be a subfolder of the project of "
            f"the app, not its root (storage://{project_root})"
        )
        raise ValueError(msg)
    return ApoloFilesPath(path=f"storage://{uri.host}/{'/'.join(parts)}")


def _check_env_names(input_: TritonAppInputs) -> None:
    for env_var in input_.extra_env_vars:
        if not ENV_NAME_RE.fullmatch(env_var.name):
            msg = (
                f"Environment variable name {env_var.name!r} must start with a "
                "letter or '_' and contain only letters, digits and '_'"
            )
            raise ValueError(msg)
        if env_var.name in YAML_SCALAR_ENV_NAMES:
            msg = (
                f"Environment variable name {env_var.name!r} is not allowed: "
                "the chart writes names unquoted and YAML reads it as a boolean "
                "or null"
            )
            raise ValueError(msg)
        if env_var.name.startswith(VERTEX_AI_ENV_PREFIX):
            msg = (
                f"Environment variable {env_var.name} is not allowed: with AIP_MODE "
                "set the Triton image runs in Vertex AI mode and the server does "
                "not serve the HTTP and gRPC endpoints of the app"
            )
            raise ValueError(msg)


async def _get_image(
    client: apolo_sdk.Client, repository: str, tag: str | None
) -> dict[str, str]:
    name, _, digest = repository.partition("@")
    if not digest and tag and tag.startswith("sha256:"):
        digest = tag
    if digest:
        if name.startswith("image:") or not DIGEST_RE.fullmatch(digest):
            msg = (
                f"Image {repository}: a digest must be sha256 with 64 hex digits, "
                "on an image outside the platform registry"
            )
            raise ValueError(msg)
        await get_image_docker_url(client=client, image=name, tag="latest")
        return {"repository": name, "tag": "", "digest": digest}
    if not tag or not tag.strip():
        msg = (
            f"Image {repository} has no tag: set a tag such as 26.10-py3 "
            "or a sha256 digest; the app does not fall back to latest"
        )
        raise ValueError(msg)
    image_url = await get_image_docker_url(client=client, image=repository, tag=tag)
    if repository.startswith("image:"):
        repository, tag = image_url.rsplit(":", 1)
    return {"repository": repository, "tag": tag, "digest": ""}


def _build_args(input_: TritonAppInputs) -> list[str]:
    return [
        "tritonserver",
        f"--model-repository={MODEL_REPOSITORY_PATH}",
        f"--http-port={HTTP_PORT}",
        f"--grpc-port={GRPC_PORT}",
        f"--metrics-port={METRICS_PORT}",
        *(_escape(arg) for arg in input_.server_extra_args),
    ]


def _build_env(
    input_: TritonAppInputs, app_secrets_name: str
) -> list[dict[str, t.Any]]:
    env: dict[str, t.Any] = {}
    if input_.hf_cache:
        env["HF_HOME"] = HF_CACHE_PATH
    if input_.hf_token:
        env["HF_TOKEN"] = serialize_optional_secret(
            input_.hf_token.token, app_secrets_name
        )
    for env_var in input_.extra_env_vars:
        env.pop(env_var.name, None)
        env[env_var.name] = env_var.deserialize_value(app_secrets_name)
    return [
        {
            "name": name,
            "value": value if isinstance(value, dict) else _escape(str(value)),
        }
        for name, value in env.items()
    ]


def _build_probe(path: str, period: int, failure_threshold: int) -> dict[str, t.Any]:
    return {
        "httpGet": {"path": path, "port": "http"},
        "periodSeconds": period,
        "failureThreshold": failure_threshold,
        "timeoutSeconds": PROBE_TIMEOUT_SECONDS,
    }


def _build_ingress(
    host: str, annotations: dict[str, str], port_name: str
) -> dict[str, t.Any]:
    return {
        "enabled": True,
        "className": INGRESS_CLASS_NAME,
        "annotations": annotations,
        "hosts": [
            {
                "host": host,
                "paths": [{"path": "/", "pathType": "Prefix", "portName": port_name}],
            }
        ],
    }


def _build_networking(
    input_: TritonAppInputs, extra_values: dict[str, t.Any]
) -> dict[str, t.Any]:
    ingress = extra_values.get("ingress") or {}
    grpc = ingress.get("grpc") or {}
    return {
        "ingress": _build_ingress(
            ingress["hosts"][0]["host"], ingress.get("annotations", {}), "http"
        )
        if input_.ingress_http
        else {"enabled": False},
        "extraServices": [
            {
                "name": GRPC_SERVICE_NAME,
                "annotations": {SERVERS_SCHEME_ANNOTATION: "h2c"},
                "ports": [{"name": "grpc", "containerPort": GRPC_PORT}],
                "ingress": _build_ingress(
                    grpc["hosts"][0]["host"],
                    {
                        key: value
                        for key, value in grpc.get("annotations", {}).items()
                        if key != SERVERS_SCHEME_ANNOTATION
                    },
                    "grpc",
                ),
            }
        ]
        if input_.ingress_grpc
        else [],
    }


class TritonAppChartValueProcessor(BaseChartValueProcessor[TritonAppInputs]):
    async def gen_extra_values(
        self,
        input_: TritonAppInputs,
        app_name: str,
        namespace: str,
        app_id: str,
        app_secrets_name: str,
        *args: t.Any,
        **kwargs: t.Any,
    ) -> dict[str, t.Any]:
        _check_server_args(input_)
        _check_env_names(input_)
        preset = get_preset(self.client, input_.preset.name)
        if preset.memory < MIN_MEMORY_BYTES:
            msg = (
                f"Preset {input_.preset.name} has {preset.memory // 10**6} MB "
                "of memory, Triton needs at least 1 GB"
            )
            raise ValueError(msg)
        model_repository = _get_project_path(
            self.client, input_.model_repository.files_path, "Model repository"
        )
        hf_cache = (
            _get_project_path(
                self.client, input_.hf_cache.files_path, "Hugging Face cache"
            )
            if input_.hf_cache
            else None
        )

        extra_values = await gen_extra_values(
            apolo_client=self.client,
            preset_type=input_.preset,
            app_id=app_id,
            app_type=AppType.Triton,
            namespace=namespace,
            ingress_http=input_.ingress_http,
            ingress_grpc=input_.ingress_grpc,
        )

        mounts = [
            ApoloFilesMount(
                storage_uri=model_repository,
                mount_path=MountPath(path=MODEL_REPOSITORY_PATH),
                mode=ApoloMountMode(mode=ApoloMountModes.RO),
            )
        ]
        if hf_cache:
            mounts.append(
                ApoloFilesMount(
                    storage_uri=hf_cache,
                    mount_path=MountPath(path=HF_CACHE_PATH),
                    mode=ApoloMountMode(mode=ApoloMountModes.RW),
                )
            )

        image = input_.image
        image_values = await _get_image(self.client, image.repository, image.tag)
        dockerconfig = await resolve_image_dockerconfig(
            client=self.client, image=image, sa_name=f"triton-{app_name}"
        )

        return {
            "fullnameOverride": get_fullname(app_id),
            "apolo_app_id": extra_values["apolo_app_id"],
            "preset_name": extra_values["preset_name"],
            "labels": {"application": APPLICATION_LABEL},
            "strategy": {"type": "Recreate"},
            "progressDeadlineSeconds": STARTUP_PERIOD_SECONDS
            * STARTUP_FAILURE_THRESHOLD
            + PROGRESS_DEADLINE_MARGIN_SECONDS,
            "image": {
                **image_values,
                "pullPolicy": image.pull_policy.value,
            },
            "dockerconfigjson": dockerconfig.filecontents if dockerconfig else None,
            "resources": extra_values["resources"],
            "tolerations": extra_values["tolerations"],
            "affinity": extra_values["affinity"],
            "podLabels": {
                **{
                    key: value
                    for key, value in extra_values["podLabels"].items()
                    if key not in CHART_POD_LABELS
                },
                **gen_apolo_storage_integration_labels(
                    client=self.client, inject_storage=True
                ),
            },
            "podAnnotations": append_apolo_storage_integration_annotations(
                {}, mounts, self.client
            ),
            "container": {
                "args": _build_args(input_),
                "env": _build_env(input_, app_secrets_name),
            },
            "service": {
                "ports": [
                    {"name": "http", "containerPort": HTTP_PORT},
                    {"name": "grpc", "containerPort": GRPC_PORT},
                    {"name": "metrics", "containerPort": METRICS_PORT},
                ]
            },
            "health_checks": {
                "startupProbe": _build_probe(
                    "/v2/health/live",
                    STARTUP_PERIOD_SECONDS,
                    STARTUP_FAILURE_THRESHOLD,
                ),
                "livenessProbe": _build_probe("/v2/health/live", 30, 9),
                "readinessProbe": _build_probe("/v2/health/ready", 10, 3),
            },
            "volumes": [{"name": "dshm", "emptyDir": {"medium": "Memory"}}],
            "volumeMounts": [{"name": "dshm", "mountPath": "/dev/shm"}],
            **_build_networking(input_, extra_values),
        }
