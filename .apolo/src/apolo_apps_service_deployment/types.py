from apolo_app_types.protocols.custom_deployment import (
    # later, this class definitions will move here,
    # for now, leaving it in the origin repo since we are actively updating it
    CustomDeploymentInputs as ServiceDeploymentInputs,  # noqa: F401
    # apart from it, this definition might still be in shared repo,
    # since it's used by other apps
    CustomDeploymentOutputs as ServiceDeploymentOutputs,  # noqa: F401
)
