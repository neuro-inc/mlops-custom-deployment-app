import typing as t

from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.outputs.shell import get_shell_outputs

from .app_types import N8nAppOutputs


class N8nAppOutputProcessor(BaseAppOutputsProcessor[N8nAppOutputs]):
    async def _generate_outputs(
        self,
        helm_values: dict[str, t.Any],
        app_instance_id: str,
    ) -> N8nAppOutputs:
        res = await get_shell_outputs(helm_values, app_instance_id)
        return N8nAppOutputs.model_validate(res)
