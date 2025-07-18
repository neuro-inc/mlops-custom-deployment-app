from apolo_apps_service_deployment.inputs_processor import (
    ServiceDeploymentInputsProcessor,
)
from apolo_apps_service_deployment.outputs_processor import (
    ServiceDeploymentOutputsProcessor,
)
from apolo_apps_service_deployment.types import (
    ServiceDeploymentInputs,
    ServiceDeploymentOutputs,
)


APOLO_APP_ID = "service-deployment"


__all__ = [
    "APOLO_APP_ID",
    "ServiceDeploymentOutputsProcessor",
    "ServiceDeploymentInputsProcessor",
    "ServiceDeploymentInputs",
    "ServiceDeploymentOutputs",
]
