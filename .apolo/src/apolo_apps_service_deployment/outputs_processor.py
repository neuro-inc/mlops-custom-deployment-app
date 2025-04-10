import typing as t

from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.outputs.custom_deployment import get_custom_deployment_outputs

from .types import ServiceDeploymentOutputs


class ServiceDeploymentOutputProcessor(
    BaseAppOutputsProcessor[ServiceDeploymentOutputs]
):
    async def _generate_outputs(
        self,
        helm_values: dict[str, t.Any],
    ) -> ServiceDeploymentOutputs:
        return ServiceDeploymentOutputs.model_validate(
            **(await get_custom_deployment_outputs(helm_values))
        )
