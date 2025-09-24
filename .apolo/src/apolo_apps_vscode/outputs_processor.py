import typing as t

from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.outputs.vscode import get_vscode_outputs

from .types import VSCodeAppOutputs


class VSCodeOutputProcessor(BaseAppOutputsProcessor[VSCodeAppOutputs]):
    async def _generate_outputs(
        self,
        helm_values: dict[str, t.Any],
        app_instance_id: str,
    ) -> VSCodeAppOutputs:
        return VSCodeAppOutputs.model_validate(
            **(await get_vscode_outputs(helm_values, app_instance_id))
        )
