import base64
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from apolo_app_types_fixtures.constants import (
    APP_ID,
    APP_SECRETS_NAME,
    DEFAULT_CLUSTER_NAME,
    DEFAULT_NAMESPACE,
    DEFAULT_ORG_NAME,
    DEFAULT_PROJECT_NAME,
)
from apolo_apps_triton.inputs_processor import TritonAppChartValueProcessor
from apolo_apps_triton.types import TritonAppInputs
from apolo_sdk._parsing_utils import _ImageNameParser
from yarl import URL

from apolo_app_types.protocols.common import (
    ApoloAuth,
    ApoloFilesPath,
    ApoloSecret,
    ContainerImage,
    CustomAuth,
    Env,
    IngressGrpc,
    IngressHttp,
    NoAuth,
    Preset,
)
from apolo_app_types.protocols.common.hugging_face import (
    HuggingFaceCache,
    HuggingFaceToken,
)
from apolo_app_types.protocols.common.middleware import AuthIngressMiddleware
from apolo_app_types.protocols.dockerhub import DockerConfigModel
from apolo_app_types.protocols.triton import TritonModelRepository


PROJECT_ROOT = (
    f"storage://{DEFAULT_CLUSTER_NAME}/{DEFAULT_ORG_NAME}/{DEFAULT_PROJECT_NAME}"
)
HTTP_HOST = f"triton--{APP_ID}.apps.some.org.neu.ro"
GRPC_HOST = f"triton-grpc--{APP_ID}.apps.some.org.neu.ro"
AUTH_MIDDLEWARE = {
    "traefik.ingress.kubernetes.io/router.middlewares": (
        "platform-platform-control-plane-ingress-auth@kubernetescrd"
    )
}
CUSTOM_AUTH = CustomAuth(middleware=AuthIngressMiddleware(name="platform-custom-auth"))


async def generate(apolo_client, inputs):
    processor = TritonAppChartValueProcessor(client=apolo_client)
    return await processor.gen_extra_values(
        input_=inputs,
        app_name="triton-app",
        namespace=DEFAULT_NAMESPACE,
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )


def server_args(values):
    return values["container"]["args"][5:]


def grpc_ingress(values):
    return values["extraServices"][0]["ingress"]


def with_args(inputs, *args, **update):
    return inputs.model_copy(update={"server_extra_args": list(args), **update})


def with_repository(inputs, path):
    return inputs.model_copy(
        update={
            "model_repository": TritonModelRepository(
                files_path=ApoloFilesPath(path=path)
            )
        }
    )


async def test_minimal_values(setup_clients, minimal_inputs):
    values = await generate(setup_clients, minimal_inputs)

    assert values["fullnameOverride"] == f"triton-{APP_ID}"
    assert values["apolo_app_id"] == APP_ID
    assert values["preset_name"] == "cpu-small"
    assert values["image"] == {
        "repository": "nvcr.io/nvidia/tritonserver",
        "tag": "26.10-py3",
        "digest": "",
        "pullPolicy": "IfNotPresent",
    }
    assert values["dockerconfigjson"] is None
    assert values["resources"]["limits"] == {"cpu": "1000.0m", "memory": "954M"}
    assert values["labels"] == {"application": "triton"}
    assert values["strategy"] == {"type": "Recreate"}
    assert values["progressDeadlineSeconds"] == 2100
    assert values["podLabels"] == {
        "platform.apolo.us/inject-storage": "true",
        "platform.apolo.us/org": DEFAULT_ORG_NAME,
        "platform.apolo.us/project": DEFAULT_PROJECT_NAME,
    }
    assert json.loads(values["podAnnotations"]["platform.apolo.us/inject-storage"]) == [
        {
            "storage_uri": f"{PROJECT_ROOT}/triton/models",
            "mount_path": "/models",
            "mount_mode": "r",
        }
    ]
    assert values["container"] == {
        "args": [
            "tritonserver",
            "--model-repository=/models",
            "--http-port=8000",
            "--grpc-port=8001",
            "--metrics-port=8002",
        ],
        "env": [],
    }
    assert values["service"] == {
        "ports": [
            {"name": "http", "containerPort": 8000},
            {"name": "grpc", "containerPort": 8001},
            {"name": "metrics", "containerPort": 8002},
        ]
    }
    assert values["health_checks"] == {
        "startupProbe": probe("/v2/health/live", 10, 180),
        "livenessProbe": probe("/v2/health/live", 30, 9),
        "readinessProbe": probe("/v2/health/ready", 10, 3),
    }
    assert values["volumes"] == [{"name": "dshm", "emptyDir": {"medium": "Memory"}}]
    assert values["volumeMounts"] == [{"name": "dshm", "mountPath": "/dev/shm"}]
    assert values["ingress"] == {"enabled": False}
    assert values["extraServices"] == []


def probe(path, period, failure_threshold):
    return {
        "httpGet": {"path": path, "port": "http"},
        "periodSeconds": period,
        "failureThreshold": failure_threshold,
        "timeoutSeconds": 2,
    }


def ingress(host, annotations, port_name):
    return {
        "enabled": True,
        "className": "traefik",
        "annotations": annotations,
        "hosts": [
            {
                "host": host,
                "paths": [{"path": "/", "pathType": "Prefix", "portName": port_name}],
            }
        ],
    }


@pytest.mark.parametrize(
    ("http", "grpc"), [(False, False), (True, False), (False, True), (True, True)]
)
async def test_ingress_combinations(setup_clients, minimal_inputs, http, grpc):
    inputs = minimal_inputs.model_copy(
        update={
            "ingress_http": IngressHttp() if http else None,
            "ingress_grpc": IngressGrpc() if grpc else None,
        }
    )

    values = await generate(setup_clients, inputs)

    assert values["ingress"] == (
        ingress(HTTP_HOST, AUTH_MIDDLEWARE, "http") if http else {"enabled": False}
    )
    assert values["extraServices"] == (
        [
            {
                "name": "grpc",
                "annotations": {
                    "traefik.ingress.kubernetes.io/service.serversscheme": "h2c"
                },
                "ports": [{"name": "grpc", "containerPort": 8001}],
                "ingress": ingress(
                    GRPC_HOST,
                    {
                        "traefik.ingress.kubernetes.io/router.entrypoints": (
                            "websecure"
                        ),
                        **AUTH_MIDDLEWARE,
                    },
                    "grpc",
                ),
            }
        ]
        if grpc
        else []
    )


async def test_grpc_host_label_parses_as_the_instance_id(setup_clients, minimal_inputs):
    values = await generate(
        setup_clients, minimal_inputs.model_copy(update={"ingress_grpc": IngressGrpc()})
    )

    label = grpc_ingress(values)["hosts"][0]["host"].split(".")[0]
    assert len(label) <= 63
    assert label.split("--", 1)[1] == APP_ID


async def test_ingress_without_auth_and_with_custom_auth(setup_clients, minimal_inputs):
    inputs = minimal_inputs.model_copy(
        update={
            "ingress_http": IngressHttp(auth=NoAuth()),
            "ingress_grpc": IngressGrpc(auth=CUSTOM_AUTH),
        }
    )

    values = await generate(setup_clients, inputs)

    assert values["ingress"]["annotations"] == {}
    assert grpc_ingress(values)["annotations"] == {
        "traefik.ingress.kubernetes.io/router.entrypoints": "websecure",
        "traefik.ingress.kubernetes.io/router.middlewares": (
            "platform-custom-auth@kubernetescrd"
        ),
    }


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("storage:triton/models", f"{PROJECT_ROOT}/triton/models"),
        (f"{PROJECT_ROOT}/triton/models", f"{PROJECT_ROOT}/triton/models"),
        (f"{PROJECT_ROOT}/", PROJECT_ROOT),
        (f"storage:/{DEFAULT_PROJECT_NAME}/models", f"{PROJECT_ROOT}/models"),
        ("storage:my models", f"{PROJECT_ROOT}/my models"),
        ("storage:моделі", f"{PROJECT_ROOT}/моделі"),
        (f"{PROJECT_ROOT}/my models", f"{PROJECT_ROOT}/my models"),
        (f"{PROJECT_ROOT}/my%20models", f"{PROJECT_ROOT}/my models"),
        (
            f"{PROJECT_ROOT}/%D0%BC%D0%BE%D0%B4%D0%B5%D0%BB%D1%96",
            f"{PROJECT_ROOT}/моделі",
        ),
        (f"{PROJECT_ROOT}/triton%2Fmodels", f"{PROJECT_ROOT}/triton/models"),
        (f"{PROJECT_ROOT}/./triton//models/", f"{PROJECT_ROOT}/triton/models"),
    ],
)
async def test_model_repository_in_the_project(
    setup_clients, minimal_inputs, path, expected
):
    values = await generate(setup_clients, with_repository(minimal_inputs, path))

    mounts = json.loads(values["podAnnotations"]["platform.apolo.us/inject-storage"])
    assert mounts[0]["storage_uri"] == expected


@pytest.mark.parametrize(
    "path",
    [
        f"storage://{DEFAULT_CLUSTER_NAME}/{DEFAULT_ORG_NAME}/other-project/models",
        f"storage://{DEFAULT_CLUSTER_NAME}/other-org/{DEFAULT_PROJECT_NAME}/models",
        f"storage://other-cluster/{DEFAULT_ORG_NAME}/{DEFAULT_PROJECT_NAME}/models",
        f"{PROJECT_ROOT}-other/models",
        "storage:/other-project/models",
        f"{PROJECT_ROOT}/../other-project/models",
        f"{PROJECT_ROOT}/..%2fother-project/models",
        f"{PROJECT_ROOT}/triton/..%2F..%2Fother-project/models",
        "storage:..%2fother-project/models",
        "storage:triton/..%2f..%2fother-project/models",
    ],
)
async def test_model_repository_outside_the_project_is_refused(
    setup_clients, minimal_inputs, path
):
    with pytest.raises(ValueError, match="must be in the project of the app"):
        await generate(setup_clients, with_repository(minimal_inputs, path))


async def test_hugging_face_cache_path_is_decoded(setup_clients, minimal_inputs):
    inputs = minimal_inputs.model_copy(
        update={
            "hf_cache": HuggingFaceCache(
                files_path=ApoloFilesPath(path="storage:hf cache/моделі")
            )
        }
    )

    values = await generate(setup_clients, inputs)

    mounts = json.loads(values["podAnnotations"]["platform.apolo.us/inject-storage"])
    assert mounts[1] == {
        "storage_uri": f"{PROJECT_ROOT}/hf cache/моделі",
        "mount_path": "/root/.cache/huggingface",
        "mount_mode": "rw",
    }


@pytest.mark.parametrize(
    "path",
    [
        f"storage://{DEFAULT_CLUSTER_NAME}/{DEFAULT_ORG_NAME}/other-project/hf",
        f"{PROJECT_ROOT}/..%2fother-project/hf",
    ],
)
async def test_hugging_face_cache_outside_the_project_is_refused(
    setup_clients, minimal_inputs, path
):
    inputs = minimal_inputs.model_copy(
        update={"hf_cache": HuggingFaceCache(files_path=ApoloFilesPath(path=path))}
    )

    with pytest.raises(
        ValueError, match="Hugging Face cache .* must be in the project of the app"
    ):
        await generate(setup_clients, inputs)


async def test_hugging_face_cache_and_token(setup_clients, minimal_inputs):
    inputs = minimal_inputs.model_copy(
        update={
            "hf_cache": HuggingFaceCache(
                files_path=ApoloFilesPath(path="storage:.apps/hugging-face-cache")
            ),
            "hf_token": HuggingFaceToken(
                token_name="hf", token=ApoloSecret(key="hf-token")
            ),
        }
    )

    values = await generate(setup_clients, inputs)

    assert json.loads(values["podAnnotations"]["platform.apolo.us/inject-storage"]) == [
        {
            "storage_uri": f"{PROJECT_ROOT}/triton/models",
            "mount_path": "/models",
            "mount_mode": "r",
        },
        {
            "storage_uri": f"{PROJECT_ROOT}/.apps/hugging-face-cache",
            "mount_path": "/root/.cache/huggingface",
            "mount_mode": "rw",
        },
    ]
    assert values["container"]["env"] == [
        {"name": "HF_HOME", "value": "/root/.cache/huggingface"},
        {
            "name": "HF_TOKEN",
            "value": {
                "valueFrom": {
                    "secretKeyRef": {"name": APP_SECRETS_NAME, "key": "hf-token"}
                }
            },
        },
    ]


async def test_extra_env_comes_last_and_overrides(setup_clients, minimal_inputs):
    inputs = minimal_inputs.model_copy(
        update={
            "hf_cache": HuggingFaceCache(
                files_path=ApoloFilesPath(path="storage:hf-cache")
            ),
            "hf_token": HuggingFaceToken(
                token_name="hf", token=ApoloSecret(key="hf-token")
            ),
            "extra_env_vars": [
                Env(name="HF_HOME", value="/root/.cache/huggingface/custom"),
                Env(name="IT323_EXTRA", value="ok"),
                Env(name="IT323_SECRET", value=ApoloSecret(key="it323-secret")),
            ],
        }
    )

    values = await generate(setup_clients, inputs)

    assert values["container"]["env"] == [
        {
            "name": "HF_TOKEN",
            "value": {
                "valueFrom": {
                    "secretKeyRef": {"name": APP_SECRETS_NAME, "key": "hf-token"}
                }
            },
        },
        {"name": "HF_HOME", "value": "/root/.cache/huggingface/custom"},
        {"name": "IT323_EXTRA", "value": "ok"},
        {
            "name": "IT323_SECRET",
            "value": {
                "valueFrom": {
                    "secretKeyRef": {"name": APP_SECRETS_NAME, "key": "it323-secret"}
                }
            },
        },
    ]


async def test_server_extra_args_are_passed_through(setup_clients, minimal_inputs):
    args = ["--log-verbose=1", "--exit-on-error=false", "--strict-readiness=false"]

    values = await generate(setup_clients, with_args(minimal_inputs, *args))

    assert server_args(values) == args


@pytest.mark.parametrize(
    ("args", "flags"),
    [
        (["--http-port=9000"], "--http-port"),
        (["--http-port", "9000"], "--http-port"),
        (["--http-p=9000"], "--http-port"),
        (["--http-port=9000", "--http-port=9100"], "--http-port"),
        (["--log-verbose=1", "--grpc-port=9001"], "--grpc-port"),
        (["--metrics-port=9002"], "--metrics-port"),
        (["--http-address=127.0.0.1"], "--http-address"),
        (["--grpc-address=127.0.0.1"], "--grpc-address"),
        (["--metrics-address=127.0.0.1"], "--metrics-address"),
        (["--allow-http=false"], "--allow-http"),
        (["--allow-grpc=false"], "--allow-grpc"),
        (["--grpc-use-ssl=true"], "--grpc-use-ssl"),
        (["--grpc-use-ssl-mutual=true"], "--grpc-use-ssl-mutual"),
        (["--grpc-use-ssl-m=true"], "--grpc-use-ssl-mutual"),
        (["--grpc-server-cert", "/c"], "--grpc-server-cert"),
        (["--grpc-server-key=/k"], "--grpc-server-key"),
        (["--grpc-root-cert=/r"], "--grpc-root-cert"),
        (["--http-port=9000", "--grpc-port=9001"], "--grpc-port, --http-port"),
    ],
)
async def test_forbidden_server_args_are_refused(
    setup_clients, minimal_inputs, args, flags
):
    with pytest.raises(ValueError, match=f"must not set {flags}:"):
        await generate(setup_clients, with_args(minimal_inputs, *args))


@pytest.mark.parametrize(
    "args", [[""], ["   "], ["--log-verbose=1", ""], ["--log-verbose", " "]]
)
async def test_empty_server_args_are_refused(setup_clients, minimal_inputs, args):
    with pytest.raises(ValueError, match="must not contain empty items"):
        await generate(setup_clients, with_args(minimal_inputs, *args))


@pytest.mark.parametrize("arg", ["--http=9000", "--grpc-use=true", "--allow=true"])
async def test_ambiguous_server_args_are_refused(setup_clients, minimal_inputs, arg):
    with pytest.raises(ValueError, match="is ambiguous"):
        await generate(setup_clients, with_args(minimal_inputs, arg))


@pytest.mark.parametrize(
    "args",
    [
        ["--allow-metrics=false"],
        ["--http-restricted-api=model-repository:admin-key=secret"],
        ["--grpc-restricted-protocol=model-repository:admin-key=secret"],
        ["--allow-sagemaker=true"],
        ["--allow-vertex-ai=true"],
        ["--model-store=/models"],
        ["--log-verbose", "1"],
        ["--unknown-flag=1"],
        ["plain-value"],
    ],
)
async def test_allowed_server_args(setup_clients, minimal_inputs, args):
    values = await generate(setup_clients, with_args(minimal_inputs, *args))

    assert server_args(values) == args


EXPLICIT_MODE_ARGS = [
    ["--model-control-mode=explicit"],
    ["--model-control-mode=EXPLICIT"],
    ["--model-control-mode", "explicit"],
    ["--model-control=explicit"],
    ["--model-control-mode=explicit", "--load-model=*"],
    ["--model-control-mode=none", "--model-control-mode=explicit"],
    ["--model-control-mode=none", "--model-control-mode", "Explicit"],
    ["--model-control-mode=explicit", "--model-control-mode=none"],
    ["--model-control-mode=explicit", "--id", "--model-control-mode=none"],
    ["--model-control-mode=explicit", "--log-file", "--model-control-mode=none"],
]


@pytest.mark.parametrize("args", EXPLICIT_MODE_ARGS)
@pytest.mark.parametrize(
    "update",
    [
        {"ingress_http": IngressHttp(auth=NoAuth())},
        {"ingress_grpc": IngressGrpc(auth=NoAuth())},
        {"ingress_http": IngressHttp(), "ingress_grpc": IngressGrpc(auth=NoAuth())},
    ],
)
async def test_explicit_mode_with_an_open_endpoint_is_refused(
    setup_clients, minimal_inputs, args, update
):
    with pytest.raises(ValueError, match="without authentication is not allowed"):
        await generate(setup_clients, with_args(minimal_inputs, *args, **update))


@pytest.mark.parametrize("args", EXPLICIT_MODE_ARGS)
@pytest.mark.parametrize(
    "update",
    [
        {},
        {"ingress_http": IngressHttp(), "ingress_grpc": IngressGrpc()},
        {"ingress_http": IngressHttp(auth=ApoloAuth())},
        {
            "ingress_http": IngressHttp(auth=CUSTOM_AUTH),
            "ingress_grpc": IngressGrpc(auth=CUSTOM_AUTH),
        },
    ],
)
async def test_explicit_mode_with_authentication_is_accepted(
    setup_clients, minimal_inputs, args, update
):
    values = await generate(setup_clients, with_args(minimal_inputs, *args, **update))

    assert server_args(values) == args


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--model-control-mode=none"],
        ["--model-control-mode=poll"],
        ["--model-control-mode", "none"],
    ],
)
async def test_open_endpoints_without_explicit_mode_are_accepted(
    setup_clients, minimal_inputs, args
):
    inputs = with_args(
        minimal_inputs,
        *args,
        ingress_http=IngressHttp(auth=NoAuth()),
        ingress_grpc=IngressGrpc(auth=NoAuth()),
    )

    values = await generate(setup_clients, inputs)

    assert values["ingress"]["annotations"] == {}
    assert grpc_ingress(values)["annotations"] == {
        "traefik.ingress.kubernetes.io/router.entrypoints": "websecure"
    }


@pytest.mark.parametrize(
    ("preset", "memory"), [("cpu-small", "954M"), ("cpu-large", "16384M")]
)
async def test_presets_with_enough_memory(
    setup_clients, minimal_inputs, preset, memory
):
    inputs = minimal_inputs.model_copy(update={"preset": Preset(name=preset)})

    values = await generate(setup_clients, inputs)

    assert values["resources"]["limits"]["memory"] == memory


@pytest.mark.parametrize(("preset", "mb"), [("cpu-micro", 104), ("cpu-999", 999)])
async def test_presets_with_too_little_memory_are_refused(
    setup_clients, minimal_inputs, preset, mb
):
    inputs = minimal_inputs.model_copy(update={"preset": Preset(name=preset)})

    with pytest.raises(
        ValueError, match=f"has {mb} MB of memory, Triton needs at least 1 GB"
    ):
        await generate(setup_clients, inputs)


async def test_private_image_gets_a_pull_secret(setup_clients, minimal_inputs):
    inputs = minimal_inputs.model_copy(
        update={
            "image": ContainerImage(
                repository="registry.example.com/triton",
                tag="custom",
                imagepullsecret=DockerConfigModel(filecontents="e30="),
            )
        }
    )

    values = await generate(setup_clients, inputs)

    assert values["image"]["repository"] == "registry.example.com/triton"
    assert values["image"]["tag"] == "custom"
    assert values["dockerconfigjson"] == "e30="


@pytest.mark.parametrize(
    ("args", "env"),
    [
        (["--model-control-mode=$(MODE)"], {"MODE": "explicit"}),
        (["--http-port$(E)=9000", "$(G)"], {"E": "", "G": "--allow-grpc=false"}),
        (["$(MODE)"], {"MODE": "--model-control-mode=explicit"}),
    ],
)
async def test_variable_references_in_server_args_are_refused(
    setup_clients, minimal_inputs, args, env
):
    inputs = with_args(
        minimal_inputs,
        *args,
        ingress_http=IngressHttp(auth=NoAuth()),
        extra_env_vars=[Env(name=name, value=value) for name, value in env.items()],
    )

    with pytest.raises(ValueError, match=r"must not contain \$\("):
        await generate(setup_clients, inputs)


@pytest.mark.parametrize(
    "args",
    [
        ["--http-restricted-api=health:admin-key=secret"],
        ["--http-restricted-api=metadata,Health:admin-key=secret"],
        ["--grpc-restricted-protocol", "health:admin-key=secret"],
        ["--http-restricted=health,inference:k=v"],
    ],
)
async def test_restricting_the_health_api_is_refused(
    setup_clients, minimal_inputs, args
):
    with pytest.raises(ValueError, match="must not restrict the health API"):
        await generate(setup_clients, with_args(minimal_inputs, *args))


@pytest.mark.parametrize("name", ["", "a b", "X=1", "A\nB", "1X", "IT-323"])
async def test_invalid_env_names_are_refused(setup_clients, minimal_inputs, name):
    inputs = minimal_inputs.model_copy(
        update={"extra_env_vars": [Env(name=name, value="1")]}
    )

    with pytest.raises(ValueError, match="must start with a letter or '_'"):
        await generate(setup_clients, inputs)


@pytest.mark.parametrize("name", ["AIP_MODE", "AIP_HTTP_PORT"])
async def test_vertex_ai_env_is_refused(setup_clients, minimal_inputs, name):
    inputs = minimal_inputs.model_copy(
        update={"extra_env_vars": [Env(name=name, value="PREDICTION")]}
    )

    with pytest.raises(ValueError, match="does not serve the HTTP and gRPC endpoints"):
        await generate(setup_clients, inputs)


async def test_valid_env_names_are_accepted(setup_clients, minimal_inputs):
    inputs = minimal_inputs.model_copy(
        update={
            "extra_env_vars": [Env(name="_X", value="1"), Env(name="aip_x1", value="2")]
        }
    )

    values = await generate(setup_clients, inputs)

    assert [env["name"] for env in values["container"]["env"]] == ["_X", "aip_x1"]


UNSAFE_STORAGE_PATHS = [
    "storage:triton:models",
    "storage:triton/models?x=1",
    "storage:triton/models#x",
    "storage:triton/mo\ndels",
    "storage:triton/mo\tdels",
    f"storage://user@{DEFAULT_CLUSTER_NAME}/{DEFAULT_ORG_NAME}/{DEFAULT_PROJECT_NAME}/m",
    f"storage://{DEFAULT_CLUSTER_NAME}:80/{DEFAULT_ORG_NAME}/{DEFAULT_PROJECT_NAME}/m",
    f"{PROJECT_ROOT}/triton:models",
    f"{PROJECT_ROOT}/a%0Ab",
    f"{PROJECT_ROOT}/a%7Fb",
    "storage:triton/a%09b",
    f"{PROJECT_ROOT}/a%C2%85b",
    f"{PROJECT_ROOT}/a%C2%80b",
    "storage:triton/a\u0085b",
]


@pytest.mark.parametrize("path", UNSAFE_STORAGE_PATHS)
async def test_unsafe_model_repository_paths_are_refused(
    setup_clients, minimal_inputs, path
):
    with pytest.raises(ValueError, match="Model repository .* plain storage path"):
        await generate(setup_clients, with_repository(minimal_inputs, path))


@pytest.mark.parametrize("path", UNSAFE_STORAGE_PATHS)
async def test_unsafe_hugging_face_cache_paths_are_refused(
    setup_clients, minimal_inputs, path
):
    inputs = minimal_inputs.model_copy(
        update={"hf_cache": HuggingFaceCache(files_path=ApoloFilesPath(path=path))}
    )

    with pytest.raises(ValueError, match="Hugging Face cache .* plain storage path"):
        await generate(setup_clients, inputs)


DIGEST = "sha256:" + "0123456789abcdef" * 4


@pytest.fixture
def real_image_parser(setup_clients):
    parser = _ImageNameParser(
        DEFAULT_CLUSTER_NAME,
        DEFAULT_ORG_NAME,
        DEFAULT_PROJECT_NAME,
        {DEFAULT_CLUSTER_NAME: URL("https://registry.cluster.org.neu.ro")},
    )
    setup_clients.parse.remote_image = MagicMock(
        side_effect=lambda image, **_: parser.parse_remote(image)
    )
    setup_clients.config.registry_url = URL("https://registry.cluster.org.neu.ro")
    token = base64.b64encode(json.dumps({"token": "sa-token"}).encode()).decode()
    setup_clients.service_accounts.create = AsyncMock(return_value=(MagicMock(), token))
    setup_clients.users.share = AsyncMock()
    return setup_clients


@pytest.mark.parametrize(
    ("repository", "tag", "expected"),
    [
        (
            "registry.example.com:5000/team/triton",
            "1",
            ("registry.example.com:5000/team/triton", "1", ""),
        ),
        ("localhost:5000/triton", "5", ("localhost:5000/triton", "5", "")),
        (
            "nvcr.io/nvidia/tritonserver",
            "26.10-py3",
            ("nvcr.io/nvidia/tritonserver", "26.10-py3", ""),
        ),
        (
            "image:triton",
            "v1",
            ("registry.cluster.org.neu.ro/test-org/test-project/triton", "v1", ""),
        ),
        (
            f"nvcr.io/nvidia/tritonserver@{DIGEST}",
            None,
            ("nvcr.io/nvidia/tritonserver", "", DIGEST),
        ),
        (
            "nvcr.io/nvidia/tritonserver",
            DIGEST,
            ("nvcr.io/nvidia/tritonserver", "", DIGEST),
        ),
    ],
)
async def test_image_reference_through_the_sdk_parser(
    real_image_parser, minimal_inputs, repository, tag, expected
):
    inputs = minimal_inputs.model_copy(
        update={"image": ContainerImage(repository=repository, tag=tag)}
    )

    values = await generate(real_image_parser, inputs)

    image = values["image"]
    assert (image["repository"], image["tag"], image["digest"]) == expected


@pytest.mark.parametrize(
    "repository",
    ["nvcr.io/nvidia/tritonserver@sha256:abc", f"image:triton@{DIGEST}"],
)
async def test_bad_digest_references_are_refused(
    real_image_parser, minimal_inputs, repository
):
    inputs = minimal_inputs.model_copy(
        update={"image": ContainerImage(repository=repository)}
    )

    with pytest.raises(ValueError, match="a digest must be sha256"):
        await generate(real_image_parser, inputs)


@pytest.mark.parametrize(
    "repository",
    [
        f"@{DIGEST}",
        f" @{DIGEST}",
        f"UPPER/Case Name with spaces@{DIGEST}",
        f"-nginx@{DIGEST}",
    ],
)
async def test_invalid_image_names_with_a_digest_are_refused(
    real_image_parser, minimal_inputs, repository
):
    inputs = minimal_inputs.model_copy(
        update={"image": ContainerImage(repository=repository)}
    )

    with pytest.raises(ValueError, match="image"):
        await generate(real_image_parser, inputs)


async def test_image_defaults_to_the_tested_triton_release(setup_clients):
    inputs = TritonAppInputs(
        preset=Preset(name="cpu-small"),
        model_repository=TritonModelRepository(
            files_path=ApoloFilesPath(path="storage:triton/models")
        ),
    )

    values = await generate(setup_clients, inputs)

    assert values["image"] == {
        "repository": "nvcr.io/nvidia/tritonserver",
        "tag": "26.10-py3",
        "digest": "",
        "pullPolicy": "IfNotPresent",
    }


@pytest.mark.parametrize(
    ("repository", "tag"),
    [
        ("nvcr.io/nvidia/tritonserver", None),
        ("nvcr.io/nvidia/tritonserver", ""),
        ("nvcr.io/nvidia/tritonserver", "  "),
        ("image:triton", None),
    ],
)
async def test_image_without_a_tag_is_refused(
    real_image_parser, minimal_inputs, repository, tag
):
    inputs = minimal_inputs.model_copy(
        update={"image": ContainerImage(repository=repository, tag=tag)}
    )

    with pytest.raises(ValueError, match="has no tag: set a tag such as 26.10-py3"):
        await generate(real_image_parser, inputs)
