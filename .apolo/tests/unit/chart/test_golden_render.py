import json
import re
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml
from apolo_app_types_fixtures.constants import (
    APP_ID,
    APP_SECRETS_NAME,
    DEFAULT_ORG_NAME,
    DEFAULT_POSTGRES_CREDS,
    DEFAULT_PROJECT_NAME,
)
from apolo_sdk import Preset
from neuro_config_client import NvidiaGPUPreset
from openwebui.test_model_gateway import GATEWAY_API, GATEWAY_EMBEDDINGS_API
from openwebui.test_stored_inputs import STORED_INPUTS

from apolo_app_types.outputs.utils.discovery import (
    load_app_inputs,
    load_app_preprocessor,
)


HELM = shutil.which("helm")
PROJECT_ROOT = Path(__file__).resolve().parents[4]
GOLDENS_PATH = Path(__file__).parent / "goldens"
CHART = "charts/custom-deployment"
MAX_KUBE_APP_NAME_LENGTH = 53
NAMESPACE = "platform--test-org--test-project--a5e4118c50842e7acbd85e28"
KUBE_VERSION = "1.31.0"

APPLICATIONS = {
    app["name"]: app
    for app in yaml.safe_load((PROJECT_ROOT / ".apolo/applications.yaml").read_text())
    if app["helm_path"] == CHART
}

PRESETS = {
    "cpu-small": Preset(
        cpu=1.0,
        memory=4 * 2**30,
        credits_per_hour=Decimal("0.05"),
        available_resource_pool_names=("cpu_pool",),
    ),
    "gpu-small": Preset(
        cpu=4.0,
        memory=16 * 2**30,
        nvidia_gpu=NvidiaGPUPreset(count=1, memory=16 * 10**9),
        credits_per_hour=Decimal("0.2"),
        available_resource_pool_names=("gpu_pool",),
    ),
}

POSTGRES_CREDENTIALS = DEFAULT_POSTGRES_CREDS.model_dump(mode="json")
IMAGE = {"repository": "nginx", "tag": "1.27"}
DOCKER_CONFIG = (
    "eyJhdXRocyI6eyJyZWdpc3RyeS5leGFtcGxlLmNvbSI6eyJhdXRoIjoiZFhObGNqcHdZWE56In19fQ=="
)
CHAT_API = {
    "host": "llm-host",
    "port": 8000,
    "protocol": "https",
    "base_path": "/",
    "hf_model": {"model_hf_name": "llm-model", "tokenizer_hf_name": "llm-tokenizer"},
}
EMBEDDINGS_API = {
    "host": "text-embeddings-inference-host",
    "port": 3000,
    "protocol": "https",
    "base_path": "/",
    "hf_model": {"model_hf_name": "text-embeddings-inference-model"},
}
TRITON_DIGEST = "sha256:" + "0" * 64
TRITON_AUTH = {
    "traefik.ingress.kubernetes.io/router.middlewares": (
        "platform-platform-control-plane-ingress-auth@kubernetescrd"
    )
}
TRITON_GRPC_ENTRYPOINT = {
    "traefik.ingress.kubernetes.io/router.entrypoints": "websecure"
}
HF_TOKEN_SECRET = {"secretKeyRef": {"name": APP_SECRETS_NAME, "key": "hf-token"}}
TRITON_STORAGE = [
    {
        "storage_uri": "storage://cluster/test-org/test-project/triton/models",
        "mount_path": "/models",
        "mount_mode": "r",
    }
]


def service_deployment(**fields: Any) -> dict[str, Any]:
    return {"preset": {"name": "cpu-small"}, "image": IMAGE, **fields}


def probe(config: dict[str, Any], **fields: Any) -> dict[str, Any]:
    return {"enabled": True, "health_check_config": config, **fields}


def openwebui(auth: dict[str, Any], database: dict[str, Any]) -> dict[str, Any]:
    return {
        **STORED_INPUTS,
        "networking_config": {"ingress_http": {"auth": auth}},
        "database_config": {"database": database},
    }


def triton_ingress(
    host_label: str, port_name: str, annotations: dict[str, str]
) -> dict[str, Any]:
    return {
        "enabled": True,
        "className": "traefik",
        "annotations": annotations,
        "hosts": [
            {
                "host": f"{host_label}--{APP_ID}.apps.some.org.neu.ro",
                "paths": [{"path": "/", "pathType": "Prefix", "portName": port_name}],
            }
        ],
    }


def triton_probe(path: str, period: int, failure_threshold: int) -> dict[str, Any]:
    return {
        "httpGet": {"path": path, "port": "http"},
        "periodSeconds": period,
        "failureThreshold": failure_threshold,
        "timeoutSeconds": 2,
    }


def triton(
    http: dict[str, Any] | None, grpc: dict[str, Any] | None, **fields: Any
) -> dict[str, Any]:
    return {
        "fullnameOverride": f"triton-{APP_ID}",
        "apolo_app_id": APP_ID,
        "preset_name": "gpu-small",
        "labels": {"application": "triton"},
        "strategy": {"type": "Recreate"},
        "progressDeadlineSeconds": 2100,
        "image": {
            "repository": "nvcr.io/nvidia/tritonserver",
            "tag": "26.10-py3",
            "pullPolicy": "IfNotPresent",
        },
        "podLabels": {
            "platform.apolo.us/inject-storage": "true",
            "platform.apolo.us/org": DEFAULT_ORG_NAME,
            "platform.apolo.us/project": DEFAULT_PROJECT_NAME,
        },
        "podAnnotations": {
            "platform.apolo.us/inject-storage": json.dumps(TRITON_STORAGE)
        },
        "container": {
            "args": [
                "tritonserver",
                "--model-repository=/models",
                "--http-port=8000",
                "--grpc-port=8001",
                "--metrics-port=8002",
            ],
            "env": [{"name": "HF_TOKEN", "value": {"valueFrom": HF_TOKEN_SECRET}}],
        },
        "service": {
            "ports": [
                {"name": "http", "containerPort": 8000},
                {"name": "grpc", "containerPort": 8001},
                {"name": "metrics", "containerPort": 8002},
            ]
        },
        "health_checks": {
            "startupProbe": triton_probe("/v2/health/live", 10, 180),
            "livenessProbe": triton_probe("/v2/health/live", 30, 9),
            "readinessProbe": triton_probe("/v2/health/ready", 10, 3),
        },
        "volumes": [{"name": "dshm", "emptyDir": {"medium": "Memory"}}],
        "volumeMounts": [{"name": "dshm", "mountPath": "/dev/shm"}],
        "ingress": http or {"enabled": False},
        "extraServices": [
            {
                "name": "grpc",
                "annotations": {
                    "traefik.ingress.kubernetes.io/service.serversscheme": "h2c"
                },
                "ports": [{"name": "grpc", "containerPort": 8001}],
                "ingress": grpc,
            }
        ]
        if grpc
        else [],
        **fields,
    }


CASES = [
    ("service-deployment", "minimal", service_deployment(), None),
    (
        "service-deployment",
        "ingress-disabled",
        service_deployment(networking={"ingress_http": None}),
        None,
    ),
    (
        "service-deployment",
        "no-auth",
        service_deployment(
            networking={
                "ingress_http": {"auth": {"type": "no_auth"}},
                "ports": [{"name": "http", "port": 8080}],
            }
        ),
        None,
    ),
    (
        "service-deployment",
        "custom-auth-middleware",
        service_deployment(
            networking={
                "ingress_http": {
                    "auth": {
                        "type": "custom_auth",
                        "middleware": {"name": "platform-custom-auth-middleware"},
                    }
                },
                "ports": [{"name": "web", "port": 3000, "path": "/ui"}],
            }
        ),
        None,
    ),
    (
        "service-deployment",
        "autoscaling",
        service_deployment(
            autoscaling={
                "min_replicas": 2,
                "max_replicas": 5,
                "target_cpu_utilization_percentage": 70,
                "target_memory_utilization_percentage": 85,
            }
        ),
        None,
    ),
    (
        "service-deployment",
        "config-map",
        service_deployment(
            config_map={
                "mount_path": {"path": "/etc/app"},
                "data": [
                    {"key": "settings.yaml", "value": "debug: false\nworkers: 4\n"},
                    {"key": "mode", "value": "production"},
                ],
            }
        ),
        None,
    ),
    (
        "service-deployment",
        "storage-mounts",
        service_deployment(
            storage_mounts={
                "mounts": [
                    {
                        "storage_uri": {
                            "path": "storage://cluster/test-org/test-project/data"
                        },
                        "mount_path": {"path": "/data"},
                        "mode": {"mode": "rw"},
                    },
                    {
                        "storage_uri": {
                            "path": "storage://cluster/test-org/test-project/models"
                        },
                        "mount_path": {"path": "/models"},
                        "mode": {"mode": "r"},
                    },
                ]
            }
        ),
        None,
    ),
    (
        "service-deployment",
        "health-checks",
        service_deployment(
            health_checks={
                "startup": probe(
                    {
                        "probe_type": "HTTP",
                        "port": 80,
                        "path": "/healthz",
                        "http_headers": {"X-Probe": "startup"},
                    },
                    initial_delay=10,
                    period=5,
                    failure_threshold=30,
                ),
                "liveness": probe(
                    {"probe_type": "TCP", "port": 80}, period=20, timeout=3
                ),
                "readiness": probe(
                    {"probe_type": "gRPC", "port": 9000, "service": "ready"}
                ),
            }
        ),
        None,
    ),
    (
        "service-deployment",
        "exec-probe",
        service_deployment(
            health_checks={
                "liveness": probe(
                    {"probe_type": "Exec", "command": ["cat", "/tmp/healthy"]}
                )
            }
        ),
        None,
    ),
    (
        "service-deployment",
        "image-pull-secret",
        service_deployment(
            image={
                "repository": "registry.example.com/team/app",
                "tag": "2.1.0",
                "pull_policy": "Always",
                "imagepullsecret": {"filecontents": DOCKER_CONFIG},
            }
        ),
        None,
    ),
    (
        "service-deployment",
        "env-from-secrets",
        service_deployment(
            container={
                "command": ["/bin/sh", "-c"],
                "args": ["exec nginx -g 'daemon off;'"],
                "env": [
                    {"name": "MODE", "value": "production"},
                    {"name": "API_TOKEN", "value": {"key": "api-token"}},
                ],
            },
            init_container=[
                {
                    "image": {"repository": "busybox", "tag": "1.36"},
                    "command": ["sh", "-c"],
                    "args": ["echo init"],
                    "env": [{"name": "DB_PASSWORD", "value": {"key": "db-password"}}],
                }
            ],
        ),
        None,
    ),
    (
        "service-deployment",
        "gpu-preset",
        service_deployment(preset={"name": "gpu-small"}),
        None,
    ),
    (
        "mlflow-core",
        "sqlite",
        {
            "preset": {"name": "cpu-small"},
            "ingress_http": {},
            "metadata_storage": {"database_type": "sqlite"},
            "artifact_store": {
                "path": "storage://cluster/test-org/test-project/mlflow-artifacts"
            },
        },
        None,
    ),
    (
        "mlflow-core",
        "postgres",
        {
            "preset": {"name": "cpu-small"},
            "ingress_http": {"auth": {"type": "no_auth"}},
            "metadata_storage": {"postgres_credentials": POSTGRES_CREDENTIALS},
        },
        None,
    ),
    (
        "vscode",
        "default",
        {"preset": {"name": "cpu-small"}, "vscode_specific": {}},
        None,
    ),
    (
        "vscode",
        "mlflow-and-extra-storage",
        {
            "preset": {"name": "gpu-small"},
            "vscode_specific": {},
            "extra_storage_mounts": {
                "mounts": [
                    {
                        "storage_uri": {
                            "path": "storage://cluster/test-org/test-project/datasets"
                        },
                        "mount_path": {"path": "/datasets"},
                        "mode": {"mode": "r"},
                    }
                ]
            },
            "mlflow_integration": {
                "internal_url": {
                    "host": f"mlflow-svc.{NAMESPACE}",
                    "port": 5000,
                    "protocol": "http",
                    "base_path": "/",
                }
            },
        },
        None,
    ),
    ("shell", "default", {"preset": {"name": "cpu-small"}}, None),
    (
        "shell",
        "passed-config",
        {"preset": {"name": "cpu-small"}},
        "eyJ0b2tlbiI6ICJ0ZXN0LXRva2VuIn0=",
    ),
    ("openwebui", "stored-sqlite", STORED_INPUTS, None),
    (
        "openwebui",
        "postgres-custom-auth",
        openwebui(
            {
                "type": "custom_auth",
                "middleware": {"name": "platform-custom-auth-middleware"},
            },
            {"database_type": "postgres", "credentials": POSTGRES_CREDENTIALS},
        ),
        None,
    ),
    (
        "openwebui",
        "no-auth",
        openwebui({"type": "no_auth"}, {"database_type": "sqlite"}),
        None,
    ),
    (
        "openwebui",
        "model-gateway",
        {
            **{
                key: value
                for key, value in STORED_INPUTS.items()
                if key != "llm_chat_api"
            },
            "openai_api": GATEWAY_API,
            "embeddings_api": GATEWAY_EMBEDDINGS_API,
        },
        None,
    ),
    (
        "private-gpt",
        "default",
        {
            "preset": {"name": "cpu-small"},
            "ingress_http": {},
            "llm_chat_api": CHAT_API,
            "pgvector_user": POSTGRES_CREDENTIALS,
            "embeddings_api": EMBEDDINGS_API,
            "private_gpt_specific": {"llm_temperature": 0.5},
        },
        None,
    ),
    (
        "fooocus",
        "default",
        {"preset": {"name": "gpu-small"}, "ingress_http": {}},
        None,
    ),
    (
        "jupyter",
        "default",
        {"preset": {"name": "cpu-small"}, "jupyter_specific": {}},
        None,
    ),
    (
        "jupyter",
        "custom-image",
        {
            "preset": {"name": "cpu-small"},
            "jupyter_specific": {
                "container_settings": {
                    "container_image": {"repository": "image-name", "tag": "latest"},
                    "container_config": {
                        "command": ["start-notebook.sh"],
                        "args": ["--NotebookApp.token=''"],
                    },
                }
            },
        },
        None,
    ),
]

RAW_CASES = [
    ("defaults", "chart", {}),
    (
        "unused-values",
        "chart",
        {
            "image": {"repository": "nginx", "tag": "1.27"},
            "imagePullSecrets": [{"name": "registry-credentials"}],
            "podAnnotations": {"example.com/owner": "ml-team"},
            "podSecurityContext": {"fsGroup": 1000},
            "container": {
                "entrypoint": ["/docker-entrypoint.sh"],
                "command": ["nginx"],
                "args": ["-g", "daemon off;"],
            },
            "nodeSelector": {"kubernetes.io/arch": "amd64"},
            "storageMounts": [
                {
                    "storage_path": {
                        "path": "storage://cluster/test-org/test-project/data"
                    },
                    "mount_path": {"path": "/data"},
                    "mode": {"mode": "rw"},
                }
            ],
            "service": {
                "labels": {"output-server": "true"},
                "ports": [{"name": "http", "containerPort": 8080}],
            },
            "ingress": {
                "enabled": True,
                "hosts": [
                    {
                        "host": "app.example.com",
                        "paths": [
                            {"path": "/", "pathType": "Prefix", "portName": "http"},
                            {"path": "/api", "pathType": "Exact", "portName": "http"},
                        ],
                    }
                ],
            },
        },
    ),
    (
        "service-disabled-ingress-without-hosts",
        "chart",
        {"service": {"enabled": False}, "ingress": {"enabled": True, "hosts": []}},
    ),
    ("fullname-override", "chart", {"fullnameOverride": "custom-name"}),
    ("name-override", "chart", {"nameOverride": "web"}),
    ("release-contains-chart-name", "custom-deployment", {}),
    (
        "extra-service-without-ingress",
        "chart",
        {
            "extraServices": [
                {
                    "name": "metrics",
                    "type": "NodePort",
                    "ports": [{"name": "metrics", "containerPort": 9090}],
                    "ingress": {"enabled": False},
                }
            ]
        },
    ),
    (
        "triton-both-endpoints",
        "triton",
        triton(
            triton_ingress("triton", "http", TRITON_AUTH),
            triton_ingress(
                "triton-grpc", "grpc", {**TRITON_GRPC_ENTRYPOINT, **TRITON_AUTH}
            ),
            image={
                "repository": "nvcr.io/nvidia/tritonserver",
                "digest": TRITON_DIGEST,
                "pullPolicy": "IfNotPresent",
            },
        ),
    ),
    (
        "triton-http-only-no-auth",
        "triton",
        triton(triton_ingress("triton", "http", {}), None),
    ),
    (
        "triton-grpc-only",
        "triton",
        triton(
            None,
            triton_ingress(
                "triton-grpc", "grpc", {**TRITON_GRPC_ENTRYPOINT, **TRITON_AUTH}
            ),
        ),
    ),
    (
        "triton-no-endpoints",
        "triton",
        triton(None, None),
    ),
]


@pytest.fixture
def presets_available() -> dict[str, Preset]:
    return PRESETS


def kube_app_name(app_name: str) -> str:
    suffix = f"-{APP_ID[:8]}"
    prefix = f"{DEFAULT_ORG_NAME}-{DEFAULT_PROJECT_NAME}-{app_name}"
    return prefix[: MAX_KUBE_APP_NAME_LENGTH - len(suffix)] + suffix


def render(release_name: str, values_path: Path) -> str:
    assert HELM is not None, "helm is required to render the chart"
    rendered = subprocess.run(
        [
            HELM,
            "template",
            release_name,
            str(PROJECT_ROOT / CHART),
            "--namespace",
            NAMESPACE,
            "--kube-version",
            KUBE_VERSION,
            "--values",
            str(values_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return re.sub(r"\n\n+(---\n|\Z)", r"\n\1", rendered)


def test_every_app_on_the_chart_has_a_case() -> None:
    assert APPLICATIONS
    assert {app for app, *_ in CASES} == set(APPLICATIONS)


def test_every_golden_has_a_case() -> None:
    assert {
        path.relative_to(GOLDENS_PATH) for path in GOLDENS_PATH.glob("**/*.yaml")
    } <= {Path(app) / f"{case}.yaml" for app, case, *_ in CASES} | {
        Path("chart") / f"{case}.yaml" for case, *_ in RAW_CASES
    }


def assert_matches_golden(
    request: pytest.FixtureRequest, golden_path: Path, rendered: str
) -> None:
    if request.config.getoption("--update-goldens"):
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(rendered)
    assert golden_path.exists(), f"{golden_path} is missing, run make update-goldens"
    assert rendered == golden_path.read_text()


@pytest.mark.parametrize(
    ("app_name", "case", "inputs", "passed_config"),
    [pytest.param(*case, id=f"{case[0]}-{case[1]}") for case in CASES],
)
async def test_chart_render_matches_golden(
    setup_clients: Any,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    tmp_path: Path,
    app_name: str,
    case: str,
    inputs: dict[str, Any],
    passed_config: str | None,
) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
    app = APPLICATIONS[app_name]
    inputs_class = load_app_inputs(
        app["app_type"], app["app_package_name"], app["inputs"]["types_name"]
    )
    processor_class = load_app_preprocessor(
        app["app_type"], app["app_package_name"], app["inputs"]["processor"]
    )
    assert inputs_class is not None
    assert processor_class is not None

    release_name = kube_app_name(app_name)
    values = await processor_class(setup_clients).gen_extra_values(
        input_=inputs_class.model_validate(json.loads(json.dumps(inputs))),
        app_name=release_name,
        namespace=NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )
    if passed_config:
        values["APOLO_PASSED_CONFIG"] = passed_config
    values_path = tmp_path / "values.json"
    values_path.write_text(json.dumps(values))
    rendered = render(release_name, values_path)

    assert_matches_golden(request, GOLDENS_PATH / app_name / f"{case}.yaml", rendered)


@pytest.mark.parametrize(
    ("case", "release_app_name", "values"),
    [pytest.param(*case, id=case[0]) for case in RAW_CASES],
)
def test_chart_render_of_raw_values_matches_golden(
    request: pytest.FixtureRequest,
    tmp_path: Path,
    case: str,
    release_app_name: str,
    values: dict[str, Any],
) -> None:
    values_path = tmp_path / "values.json"
    values_path.write_text(json.dumps(values))
    rendered = render(kube_app_name(release_app_name), values_path)

    assert_matches_golden(request, GOLDENS_PATH / "chart" / f"{case}.yaml", rendered)
