import logging
import typing as t

from apolo_app_types.outputs.base import BaseAppOutputsProcessor
from apolo_app_types.outputs.custom_deployment import get_custom_deployment_outputs

from .types import ServiceDeploymentOutputs


logger = logging.getLogger(__name__)


class ServiceDeploymentOutputsProcessor(
    BaseAppOutputsProcessor[ServiceDeploymentOutputs]
):
    async def _generate_outputs(
        self,
        helm_values: dict[str, t.Any],
        app_instance_id: str,
    ) -> ServiceDeploymentOutputs:
        outputs = await get_custom_deployment_outputs(helm_values, app_instance_id)
        msg = f"Got outputs: {outputs}"
        logger.info(msg)
        return ServiceDeploymentOutputs.model_validate(outputs)
