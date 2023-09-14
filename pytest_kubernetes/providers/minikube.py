from pytest_kubernetes.providers.base import AClusterManager
from pytest_kubernetes.options import ClusterOptions


class MinikubeManager(AClusterManager):
    @classmethod
    def get_binary_name(cls) -> str:
        return "minikube"

    def _on_delete(self) -> None:
        self._exec(["delete", "-p", self.cluster_name])

    def load_image(self, image: str) -> None:
        self._exec(["image", "load", image, "-p", self.cluster_name])


class MinikubeKVM2Manager(MinikubeManager):
    def _on_create(self, cluster_options: ClusterOptions, **kwargs) -> None:
        opts = kwargs.get("options", [])
        self._exec(
            [
                "start",
                "-p",
                self.cluster_name,
                "--driver",
                "kvm2",
                "--embed-certs",
                "--kubernetes-version",
                f"v{cluster_options.api_version}",
            ]
            + opts,
            additional_env={"KUBECONFIG": str(cluster_options.kubeconfig_path)},
        )


class MinikubeDockerManager(MinikubeManager):
    def _on_create(self, cluster_options: ClusterOptions, **kwargs) -> None:
        opts = kwargs.get("options", [])
        self._exec(
            [
                "start",
                "-p",
                self.cluster_name,
                "--driver",
                "docker",
                "--embed-certs",
                "--kubernetes-version",
                f"v{cluster_options.api_version}",
            ]
            + opts,
            additional_env={"KUBECONFIG": str(cluster_options.kubeconfig_path)},
        )
