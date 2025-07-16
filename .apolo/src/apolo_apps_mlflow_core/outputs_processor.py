import typing as t

from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.outputs.custom_deployment import get_custom_deployment_outputs

from .types import MLFlowAppOutputs


class MLFlowOutputProcessor(BaseAppOutputsProcessor[MLFlowAppOutputs]):
    async def _generate_outputs(
        self,
        helm_values: dict[str, t.Any],
        app_instance_id: str,
    ) -> MLFlowAppOutputs:
        return MLFlowAppOutputs.model_validate(
            **(await get_custom_deployment_outputs(helm_values, app_instance_id))
        )
