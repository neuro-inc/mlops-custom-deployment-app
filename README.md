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