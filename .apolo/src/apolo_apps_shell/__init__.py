from apolo_apps_shell.inputs_processor import ShellAppChartValueProcessor
from apolo_apps_shell.outputs_processor import ShellAppOutputProcessor
from apolo_apps_shell.app_types import ShellAppInputs, ShellAppOutputs


APOLO_APP_TYPE = "shell"


__all__ = [
    "APOLO_APP_TYPE",
    "ShellAppOutputProcessor",
    "ShellAppChartValueProcessor",
    "ShellAppInputs",
    "ShellAppOutputs",
]
