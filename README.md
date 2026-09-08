# Custom Deployment Helm Chart

This repository contains a generic Helm chart for deploying scalable applications on the Apolo platform. This chart is designed to be used as a Custom Deployment application that is installed by the Apps API.

## Structure

- `charts/custom-deployment/`: Contains the Helm chart for the custom application.
  - `.helmignore`: Patterns to ignore when packaging the chart.
  - `Chart.yaml`: Information about the chart.
  - `templates/`: Directory containing Kubernetes resource templates.
    - `_helpers.tpl`: Template helpers.
    - `deployment.yaml`: Deployment resource template.
    - `hpa.yaml`: Horizontal Pod Autoscaler resource template.
    - `ingress.yaml`: Ingress resource template.
    - `NOTES.txt`: Instructions displayed after installation.
    - `service.yaml`: Service resource template.
    - `serviceaccount.yaml`: ServiceAccount resource template.
    - `tests/`: Directory containing test templates.
      - `test-connection.yaml`: Test connection template.
  - `values.yaml`: Default values for the chart.

## Usage

To deploy the application using this Helm chart, follow these steps:

1. Customize the `values.yaml` file to suit your application's requirements.
2. Install the chart using the Helm CLI:
   ```sh
   helm install custom-deployment charts/custom-deployment
   ```

## Service Deployment static hostname

When the Apps API has global-host routing enabled for the cluster, Service Deployment accepts:

```yaml
networking:
  service_enabled: true
  ingress_http:
    static_hostname: my-api
```

The hostname label is optional. The Apps API reserves its global name and exposes `static_url` after routing and TLS verification; the generated URL remains available. This input is specific to the Service Deployment App, not a direct Helm chart value.

The companion [Apps API implementation](https://github.com/neuro-inc/platform-apps/pull/999) owns reservation, transfer, DNS, and rollout configuration. Deploy its backend, authentication, and infrastructure prerequisites before publishing this template.
