from pytest_kubernetes.providers.base import AClusterManager
from pytest_kubernetes.options import ClusterOptions
import subprocess
import re


class K3dManagerBase(AClusterManager):
    @classmethod
    def get_binary_name(self) -> str:
        return "k3d"

    @classmethod
    def get_k3d_version(self) -> str:
        version_proc = subprocess.run(
            "k3d --version",
            shell=True,
            capture_output=True,
            check=True,
            timeout=10,
        )
        version_match = re.match(
            r"k3d version v(\d+\.\d+\.\d+)", version_proc.stdout.decode()
        )
        if not version_match:
            return "0.0.0"
        return version_match.group(1)

    def _translate_version(self, version: str) -> str:
        return f"rancher/k3s:v{version}-k3s1"

    def _on_create(self, cluster_options: ClusterOptions, **kwargs) -> None:
        opts = kwargs.get("options", [])

        # see https://k3d.io/v5.1.0/usage/configfile/
        if (
            cluster_options.provider_config
            and K3dManagerBase.get_k3d_version() >= "4.0.0"
        ):
            opts += [
                "--config",
                str(cluster_options.provider_config),
                "--kubeconfig-update-default=0",
                "--wait",
                f"--timeout={cluster_options.cluster_timeout}s",
            ]
        else:
            if K3dManagerBase.get_k3d_version() < "4.0.0":
                opts += [
                    "--name",
                    self.cluster_name,
                    "--kubeconfig-update-default=0",
                    "--image",
                    self._translate_version(cluster_options.api_version),
                    "--wait",
                    f"--timeout={cluster_options.cluster_timeout}s",
                ]
            else:
                opts += [
                    self.cluster_name,
                    "--kubeconfig-update-default=0",
                    "--image",
                    self._translate_version(cluster_options.api_version),
                    "--wait",
                    f"--timeout={cluster_options.cluster_timeout}s",
                ]

        self._exec(
            [
                "cluster",
                "create",
            ]
            + opts
        )
        self._exec(
            [
                "kubeconfig",
                "get",
                self.cluster_name,
                ">",
                str(cluster_options.kubeconfig_path),
            ]
        )

    def _on_delete(self) -> None:
        self._exec(["cluster", "delete", self.cluster_name])

    def load_image(self, image: str) -> None:
        self._exec(["image", "import", image, "--cluster", self.cluster_name])
