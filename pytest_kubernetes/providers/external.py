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

    @classmethod
    def get_binary_name(cls) -> str:
        return ""

    def load_image(self, *args):
        pass

    @property
    def kubeconfig(self) -> Path | None:
        if self._kubeconfig:
            return Path(self._kubeconfig)
        return None
