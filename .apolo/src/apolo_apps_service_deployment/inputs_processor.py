from apolo_app_types.helm.apps.custom_deployment import (
    CustomDeploymentChartValueProcessor,
)

from .types import ServiceDeploymentInputs


class ServiceDeploymentInputsProcessor(CustomDeploymentChartValueProcessor):
    async def gen_extra_values(self, input_: ServiceDeploymentInputs, *args, **kwargs):
        values = await super().gen_extra_values(input_, *args, **kwargs)

        ingress = getattr(input_.networking, "ingress_http", None)
        if ingress and ingress.annotations:
            values.setdefault("ingress", {}).setdefault("annotations", {}).update(
                ingress.annotations
            )

        return values
