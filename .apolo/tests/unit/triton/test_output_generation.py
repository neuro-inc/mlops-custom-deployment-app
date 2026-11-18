import pytest
from apolo_app_types_fixtures.constants import APP_ID
from apolo_apps_triton.outputs_processor import TritonAppOutputProcessor
from apolo_apps_triton.types import TritonAppOutputs

from apolo_app_types.outputs.utils.type_search import find_instances_recursive_simple
from apolo_app_types.protocols.common import (
    ApoloSecret,
    Env,
    IngressGrpc,
    IngressHttp,
)
from apolo_app_types.protocols.common.hugging_face import HuggingFaceToken

from .conftest import NAMESPACE
from .test_input_generation import GRPC_HOST, HTTP_HOST, generate


INTERNAL_HOST = f"triton-{APP_ID}.{NAMESPACE}"


def url(host, port, protocol, api_type, type_name):
    return {
        "host": host,
        "port": port,
        "protocol": protocol,
        "timeout": 30.0,
        "base_path": "/",
        "api_type": api_type,
        "__type__": type_name,
    }


@pytest.mark.parametrize(
    ("http", "grpc"), [(False, False), (True, False), (False, True), (True, True)]
)
async def test_outputs_for_each_ingress_combination(
    setup_clients, minimal_inputs, http, grpc
):
    inputs = minimal_inputs.model_copy(
        update={
            "ingress_http": IngressHttp() if http else None,
            "ingress_grpc": IngressGrpc() if grpc else None,
        }
    )
    values = await generate(setup_clients, inputs)

    outputs = await TritonAppOutputProcessor().generate_outputs(
        helm_values=values, app_instance_id="triton-app"
    )

    http_endpoint = outputs["http_endpoint"]
    assert http_endpoint["__type__"] == "ServiceAPI[TritonServerHttpEndpoint]"
    assert http_endpoint["internal_url"] == url(
        INTERNAL_HOST, 8000, "http", "rest", "TritonServerHttpEndpoint"
    )
    assert http_endpoint["external_url"] == (
        url(HTTP_HOST, 443, "https", "rest", "TritonServerHttpEndpoint")
        if http
        else None
    )
    grpc_endpoint = outputs["grpc_endpoint"]
    assert grpc_endpoint["__type__"] == "ServiceAPI[TritonServerGRPCEndpoint]"
    assert grpc_endpoint["internal_url"] == url(
        INTERNAL_HOST, 8001, "http", "grpc", "TritonServerGRPCEndpoint"
    )
    assert grpc_endpoint["external_url"] == (
        url(GRPC_HOST, 443, "https", "grpc", "TritonServerGRPCEndpoint")
        if grpc
        else None
    )


async def test_outputs_hold_no_secrets(setup_clients, minimal_inputs):
    inputs = minimal_inputs.model_copy(
        update={
            "ingress_http": IngressHttp(),
            "hf_token": HuggingFaceToken(
                token_name="hf", token=ApoloSecret(key="hf-token")
            ),
            "extra_env_vars": [Env(name="SECRET", value=ApoloSecret(key="secret"))],
        }
    )
    values = await generate(setup_clients, inputs)

    outputs = await TritonAppOutputProcessor().generate_outputs(
        helm_values=values, app_instance_id="triton-app"
    )

    assert (
        find_instances_recursive_simple(
            obj=TritonAppOutputs.model_validate(outputs), target_type=ApoloSecret
        )
        == []
    )
    assert "hf-token" not in str(outputs)


async def test_outputs_from_chart_values_only():
    outputs = await TritonAppOutputProcessor().generate_outputs(
        helm_values={
            "fullnameOverride": "triton-abc",
            "ingress": {
                "enabled": False,
                "hosts": [{"host": "stale.example.com", "paths": []}],
            },
            "extraServices": [
                {
                    "name": "other",
                    "ingress": {
                        "enabled": True,
                        "hosts": [{"host": "other.example.com", "paths": []}],
                    },
                },
                {
                    "name": "grpc",
                    "ingress": {
                        "enabled": True,
                        "hosts": [
                            {"host": "triton-grpc--abc.example.com", "paths": []}
                        ],
                    },
                },
            ],
        },
        app_instance_id="triton-app",
    )

    assert outputs["http_endpoint"]["internal_url"]["host"] == f"triton-abc.{NAMESPACE}"
    assert outputs["http_endpoint"]["external_url"] is None
    assert outputs["grpc_endpoint"]["internal_url"]["host"] == f"triton-abc.{NAMESPACE}"
    assert outputs["grpc_endpoint"]["external_url"]["host"] == (
        "triton-grpc--abc.example.com"
    )
