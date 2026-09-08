# IT-196: Service Deployment global static hostname

The [IT-196](https://apolocloud.atlassian.net/browse/IT-196) scope is global static hostnames only for images installed through the existing Service Deployment App. The public name survives project, organization, cluster, and instance changes through an authorized binding transfer.

- [Recommended implementation](implementation-proposal.md): optional `networking.ingress_http.static_hostname`, global DNS, persistent ownership, binding transfers, outputs, authentication, TLS, and acceptance checks.
- [Generic App creation flow](../../engineering/app-development.md): reusable authoring and Dev/Prod release guidance.
- [Ticket deployment flow](app-creation-flow.md): recorded pipeline evidence and IT-196 release dependencies.
- [Apolo Main platform inspection](apolo-main-platform.md): dated routing, DNS, and TLS observations from 2026-09-07; revalidate before implementation.

**Implementation:** resolve the optional label as `<static_hostname>.apps.apolo.us` in Prod and `<static_hostname>.apps.dev.apolo.us` in Dev, independent of installation context. Keep the generated URL and route the static hostname to the bound deployment's own Service through a separate control-plane-owned route. Reserve ownership separately from the instance, retain it on detachment/uninstall, and authorize every transfer. No target selectors or separate alias App are required. Source changes are opt-in; live rollout and certificate readiness remain pending.

Choose separate Dev/Prod zones; no actual global domain has been selected or provisioned. DNS, ingress, TLS, authentication, outputs, and stale operations require coordinated lifecycle handling. Migration can interrupt traffic during cutover and DNS convergence; this is stable naming, not a zero-downtime guarantee. The proposal does not implement customer-owned custom domains or independence from Apolo's ownership of its DNS suffix.

This is an implementation proposal; no feature code or live global-domain deployment has been validated.
