from pydantic import Field

from apolo_app_types.protocols.common.schema_extra import (
    SchemaExtraMetadata,
)
from apolo_app_types.protocols.custom_deployment import (
    CustomDeploymentInputs,
    CustomDeploymentOutputs,
    Preset,
)
from apolo_app_types.protocols.vscode import (
    # later, this class definitions will move here,
    # for now, leaving it in the origin repo since we are actively updating it
    VSCodeAppInputs,  # noqa: F401
    # apart from it, this definition might still be in shared repo,
    # since it's used by other apps
    VSCodeAppOutputs,  # noqa: F401
)


class VSCodeInputs(CustomDeploymentInputs):
    preset: Preset = Field(
        ...,
        json_schema_extra=SchemaExtraMetadata(
            title="VSCode preset",
            description="Select the resource preset used for the instance. "
            "Minimal resources depends on your application needs, "
            "but a good starting point is 0.5 CPU cores and 512 MiB memory.",
        ).as_json_schema_extra(),
    )


class VSCodeOutputs(CustomDeploymentOutputs):
    pass
