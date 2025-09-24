from apolo_apps_vscode.inputs_processor import VSCodeChartValueProcessor
from apolo_apps_vscode.outputs_processor import VSCodeOutputProcessor
from apolo_apps_vscode.types import VSCodeAppInputs, VSCodeAppOutputs


APOLO_APP_TYPE = "vscode"


__all__ = [
    "APOLO_APP_TYPE",
    "VSCodeOutputProcessor",
    "VSCodeChartValueProcessor",
    "VSCodeAppInputs",
    "VSCodeAppOutputs",
]
