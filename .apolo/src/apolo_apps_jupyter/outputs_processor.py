import logging
import typing as t

from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.outputs.common import (
    INSTANCE_LABEL,
    get_internal_external_web_urls,
)
from apolo_app_types.protocols.common.networking import ServiceAPI, WebApp
from apolo_apps_jupyter.types import JupyterAppOutputs


logger = logging.getLogger()


async def get_jupyter_outputs(
    helm_values: dict[str, t.Any], app_instance_id: str
) -> JupyterAppOutputs:
    labels = {"application": "jupyter", INSTANCE_LABEL: app_instance_id}
    internal_web_app_url, external_web_app_url = await get_internal_external_web_urls(
        labels
    )

    return JupyterAppOutputs(
        app_url=ServiceAPI[WebApp](
            internal_url=internal_web_app_url,
            external_url=external_web_app_url,
        ),
    )


class JupyterOutputProcessor(BaseAppOutputsProcessor[JupyterAppOutputs]):
    async def _generate_outputs(
        self,
        helm_values: dict[str, t.Any],
        app_instance_id: str,
    ) -> JupyterAppOutputs:
        return await get_jupyter_outputs(helm_values, app_instance_id)
