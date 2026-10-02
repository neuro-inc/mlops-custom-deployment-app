import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


HELM = shutil.which("helm")
PROJECT_ROOT = Path(__file__).resolve().parents[4]
CHART_PATH = PROJECT_ROOT / "charts" / "custom-deployment"


@pytest.mark.skipif(HELM is None, reason="Helm is required to render the chart")
def test_config_map_name_matches_deployment_volume(tmp_path: Path) -> None:
    values_path = tmp_path / "values.yaml"
    values_path.write_text(
        yaml.safe_dump(
            {
                "configMap": {
                    "enabled": True,
                    "name": "service-app-configmap",
                    "data": {"settings.yaml": "debug: false"},
                },
                "volumes": [
                    {
                        "name": "service-app-configmap",
                        "configMap": {"name": "service-app-configmap"},
                    }
                ],
                "volumeMounts": [
                    {
                        "name": "service-app-configmap",
                        "mountPath": "/etc/service-config",
                    }
                ],
            }
        )
    )

    rendered = subprocess.run(
        [
            HELM,
            "template",
            "service-app",
            str(CHART_PATH),
            "--namespace",
            "test-ns",
            "--values",
            str(values_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    resources = [resource for resource in yaml.safe_load_all(rendered) if resource]
    config_map = next(
        resource for resource in resources if resource["kind"] == "ConfigMap"
    )
    deployment = next(
        resource for resource in resources if resource["kind"] == "Deployment"
    )

    assert config_map["metadata"]["name"] == "service-app-configmap"
    assert config_map["metadata"]["labels"]["application"] == "custom-deployment"

    pod_spec = deployment["spec"]["template"]["spec"]
    volume = pod_spec["volumes"][0]
    volume_mount = pod_spec["containers"][0]["volumeMounts"][0]
    assert volume["configMap"]["name"] == config_map["metadata"]["name"]
    assert volume_mount == {
        "name": volume["name"],
        "mountPath": "/etc/service-config",
    }


@pytest.mark.skipif(HELM is None, reason="Helm is required to render the chart")
def test_config_map_name_is_required() -> None:
    rendered = subprocess.run(
        [
            HELM,
            "template",
            "service-app",
            str(CHART_PATH),
            "--set",
            "configMap.enabled=true",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert rendered.returncode != 0
    assert "configMap.name is required" in rendered.stderr
