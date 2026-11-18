import typing as t

from apolo_app_types.clients.kube import get_current_namespace
from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.protocols.common import ServiceAPI
from apolo_app_types.protocols.triton import (
    TritonServerGRPCEndpoint,
    TritonServerHttpEndpoint,
)
from apolo_apps_triton.inputs_processor import GRPC_PORT, GRPC_SERVICE_NAME, HTTP_PORT
from apolo_apps_triton.types import TritonAppOutputs


INGRESS_PORT = 443


def _get_external_host(ingress: dict[str, t.Any] | None) -> str | None:
    if not ingress or not ingress.get("enabled") or not ingress.get("hosts"):
        return None
    return t.cast(str, ingress["hosts"][0]["host"])


def _get_grpc_ingress(helm_values: dict[str, t.Any]) -> dict[str, t.Any] | None:
    return next(
        (
            service.get("ingress")
            for service in helm_values.get("extraServices") or []
            if service.get("name") == GRPC_SERVICE_NAME
        ),
        None,
    )


class TritonAppOutputProcessor(BaseAppOutputsProcessor[TritonAppOutputs]):
    async def _generate_outputs(
        self,
        helm_values: dict[str, t.Any],
        app_instance_id: str,
    ) -> TritonAppOutputs:
        internal_host = f"{helm_values['fullnameOverride']}.{get_current_namespace()}"
        http_host = _get_external_host(helm_values.get("ingress"))
        grpc_host = _get_external_host(_get_grpc_ingress(helm_values))
        return TritonAppOutputs(
            http_endpoint=ServiceAPI[TritonServerHttpEndpoint](
                internal_url=TritonServerHttpEndpoint(
                    host=internal_host, port=HTTP_PORT, protocol="http"
                ),
                external_url=TritonServerHttpEndpoint(
                    host=http_host, port=INGRESS_PORT, protocol="https"
                )
                if http_host
                else None,
            ),
            grpc_endpoint=ServiceAPI[TritonServerGRPCEndpoint](
                internal_url=TritonServerGRPCEndpoint(
                    host=internal_host, port=GRPC_PORT, protocol="http"
                ),
                external_url=TritonServerGRPCEndpoint(
                    host=grpc_host, port=INGRESS_PORT, protocol="https"
                )
                if grpc_host
                else None,
            ),
        )
