from apolo_app_types.protocols.common import (
    AppInputs,
    IngressHttp,
    Preset,
)
from apolo_app_types.protocols.fooocus import FooocusAppOutputs


class FooocusAppInputs(AppInputs):
    preset: Preset
    ingress_http: IngressHttp


__all__ = ["FooocusAppInputs", "FooocusAppOutputs"]
