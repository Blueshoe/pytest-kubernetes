from pytest_kubernetes.providers.base import AClusterManager
from pytest_kubernetes.options import ClusterOptions


class KindManager(AClusterManager):
    @classmethod
    def get_binary_name(self) -> str:
        return "kind"

    def _on_create(self, cluster_options: ClusterOptions, **kwargs) -> None:
        opts = kwargs.get("options", [])
        _ = self._exec(
            [
                "create",
                "cluster",
                "--name",
                self.cluster_name,
                "--kubeconfig",
                str(cluster_options.kubeconfig_path),
                "--image",
                f"kindest/node:v{cluster_options.api_version}",
            ]
            + opts
        )

    def _on_delete(self) -> None:
        _ = self._exec(["delete", "cluster", "--name", self.cluster_name])

    def load_image(self, image: str) -> None:
        self._exec(["load", "docker-image", image, "--name", self.cluster_name])
