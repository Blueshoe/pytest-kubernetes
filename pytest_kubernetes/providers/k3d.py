from pytest_kubernetes.providers.base import AClusterManager
from pytest_kubernetes.options import ClusterOptions


class K3dManager(AClusterManager):
    @classmethod
    def get_binary_name(self) -> str:
        return "k3d"

    def _translate_version(self, version: str) -> str:
        return f"rancher/k3s:v{version}-k3s1"

    def _on_create(self, cluster_options: ClusterOptions, **kwargs) -> None:
        opts = kwargs.get("options", [])
        self._exec(
            [
                "cluster",
                "create",
                self.cluster_name,
                "--kubeconfig-update-default=0",
                "--image",
                self._translate_version(cluster_options.api_version),
                "--wait",
                f"--timeout={cluster_options.cluster_timeout}s",
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
