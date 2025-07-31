from apolo_apps_mlflow_core.inputs_processor import MLFlowChartValueProcessor
from apolo_apps_mlflow_core.outputs_processor import MLFlowOutputProcessor
from apolo_apps_mlflow_core.types import MLFlowAppInputs, MLFlowAppOutputs


APOLO_APP_TYPE = "mlflow-core"


__all__ = [
    "APOLO_APP_TYPE",
    "MLFlowOutputProcessor",
    "MLFlowChartValueProcessor",
    "MLFlowAppInputs",
    "MLFlowAppOutputs",
]
