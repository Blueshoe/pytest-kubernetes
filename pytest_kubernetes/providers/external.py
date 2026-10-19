from pathlib import Path
from pytest_kubernetes.providers.base import AClusterManager


class ExternalManagerBase(AClusterManager):
    _kubeconfig: Path | None = None

    def __init__(
        self,
        cluster_name: str | None = None,
        provider_config: str | Path | None = None,
        kubeconfig: Path | str | None = None,
    ) -> None:
        if kubeconfig is None and provider_config is not None:
            kubeconfig = Path(provider_config)
            provider_config = None
        super().__init__(
            cluster_name,
            str(provider_config) if provider_config else None,
            Path(kubeconfig) if kubeconfig else None,
        )
        if kubeconfig:
            self._kubeconfig = Path(kubeconfig)
            self._cluster_options.kubeconfig_path = Path(kubeconfig)
        elif self._kubeconfig:
            self._cluster_options.kubeconfig_path = Path(self._kubeconfig)

    def _on_create(self, *args, **kwarg) -> None:
        if self._kubeconfig:
            self._cluster_options.kubeconfig_path = self._kubeconfig

    def _ensure_executable(self) -> None:
        pass

    def _on_delete(self) -> None:
        pass

    @classmethod
    def get_binary_name(cls) -> str:
        return ""

    def load_image(self, *args):
        pass

    @property
    def kubeconfig(self) -> Path | None:
        if self._kubeconfig:
            return Path(self._kubeconfig)
        if self._cluster_options.kubeconfig_path:
            return Path(self._cluster_options.kubeconfig_path)
        return None
