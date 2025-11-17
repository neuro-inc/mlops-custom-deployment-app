import typing as t

from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.outputs.openwebui import get_openwebui_outputs

from .types import OpenWebUIAppOutputs


class OpenWebUIOutputProcessor(BaseAppOutputsProcessor[OpenWebUIAppOutputs]):
    async def _generate_outputs(
        self,
        helm_values: dict[str, t.Any],
        app_instance_id: str,
    ) -> OpenWebUIAppOutputs:
        return OpenWebUIAppOutputs.model_validate(
            await get_openwebui_outputs(helm_values, app_instance_id)
        )
