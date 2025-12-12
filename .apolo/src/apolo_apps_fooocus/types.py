from apolo_app_types.protocols.common import (
    AppInputs,
    AppOutputs,
    IngressHttp,
    Preset,
)


class FooocusAppInputs(AppInputs):
    preset: Preset
    ingress_http: IngressHttp


class FooocusAppOutputs(AppOutputs):
    pass


__all__ = ["FooocusAppInputs", "FooocusAppOutputs"]
