from pytest_kubernetes.providers.base import AClusterManager
from pytest_kubernetes.options import ClusterOptions
import yaml


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

        if cluster_options.provider_config:
            config_yaml = yaml.safe_load(cluster_options.provider_config.read_text())
            try:
                for config in config_yaml["configs"]:
                    self._exec(
                        [
                            "config",
                            config["name"],
                            f"{config['value']}",
                            "-p",
                            f"{config_yaml['name']}",
                        ],
                        additional_env={
                            "KUBECONFIG": str(cluster_options.kubeconfig_path)
                        },
                    )
            except KeyError as ex:
                raise ValueError(
                    f"Missing key: {ex}; cluster_config for minikube setup invalid. Please refer to the docs!"
                )
        else:
            opts += [
                "--driver",
                "kvm2",
                "--embed-certs",
                "--kubernetes-version",
                f"v{cluster_options.api_version}",
            ]

        self._exec(
            [
                "start",
                "-p",
                self.cluster_name,
            ]
            + opts,
            additional_env={"KUBECONFIG": str(cluster_options.kubeconfig_path)},
        )


class MinikubeDockerManager(MinikubeManager):
    def _on_create(self, cluster_options: ClusterOptions, **kwargs) -> None:
        opts = kwargs.get("options", [])

        if cluster_options.provider_config:
            config_yaml = yaml.safe_load(cluster_options.provider_config.read_text())
            try:
                for config in config_yaml["configs"]:
                    self._exec(
                        [
                            "config",
                            config["name"],
                            f"{config['value']}",
                            "-p",
                            f"{config_yaml['name']}",
                        ],
                        additional_env={
                            "KUBECONFIG": str(cluster_options.kubeconfig_path)
                        },
                    )
            except KeyError as ex:
                raise ValueError(
                    f"Missing key: {ex}; cluster_config for minikube setup invalid. Please refer to the docs!"
                )
        else:
            opts += [
                "--driver",
                "docker",
                "--embed-certs",
                "--kubernetes-version",
                f"v{cluster_options.api_version}",
            ]

        self._exec(
            [
                "start",
                "-p",
                self.cluster_name,
            ]
            + opts,
            additional_env={"KUBECONFIG": str(cluster_options.kubeconfig_path)},
        )
