from pathlib import Path
from typing import Optional
from pytest_kubernetes.providers.base import AClusterManager
from pytest_kubernetes.options import ClusterOptions


class ExternalManagerBase(AClusterManager):
    _kubeconfig = None

    def _on_create(self, *args, **kwarg) -> None:
        self._cluster_options.kubeconfig_path = self._kubeconfig

    def _ensure_executable(self) -> None:
        pass

    def _on_delete(self) -> None:
        pass

    def get_binary_name(cls) -> str:
        return ""

    def load_image(self, *args):
        pass

    @property
    def kubeconfig(self) -> Path | None:
        return Path(self._kubeconfig)

    @kubeconfig.setter
    def set_kubeconfig(self, kubeconfig: Path) -> None:
        self._kubeconfig = str(kubeconfig)
