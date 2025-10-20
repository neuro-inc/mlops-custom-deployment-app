from apolo_app_types.protocols.custom_deployment import (
    CustomDeploymentInputs,
    CustomDeploymentOutputs,
    Field,
    IngressHttp,
    SchemaExtraMetadata,
)


class ServiceDeploymentIngress(IngressHttp):
    annotations: dict[str, str] = Field(
        default_factory=dict,
        json_schema_extra=SchemaExtraMetadata(
            title="Ingress Annotations",
            description=(
                "Optional ingress annotations. " "Configure Ingress controllers."
            ),
        ).as_json_schema_extra(),
    )


class ServiceDeploymentInputs(CustomDeploymentInputs):
    networking: CustomDeploymentInputs.model_fields["networking"].annotation = Field(
        default_factory=lambda: CustomDeploymentInputs.model_fields[
            "networking"
        ].annotation(ingress_http=ServiceDeploymentIngress()),
        json_schema_extra=SchemaExtraMetadata(
            title="Networking",
            description="Networking configuration using ServiceDeploymentIngress.",
        ).as_json_schema_extra(),
    )


class ServiceDeploymentOutputs(CustomDeploymentOutputs):
    pass
