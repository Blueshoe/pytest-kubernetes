import shutil
from typing import Type
from pytest_kubernetes.providers.base import AClusterManager
from .k3d import K3dManager
from .kind import KindManager
from .minikube import MinikubeDockerManager, MinikubeKVM2Manager


def select_provider_manager(name: str | None = None) -> Type[AClusterManager]:
    if name:
        providers = {
            "k3d": K3dManager,
            "kind": KindManager,
            "minikube": MinikubeDockerManager,
            "minikube-docker": MinikubeDockerManager,
            "minikube-kvm2": MinikubeKVM2Manager,
        }
        provider = providers.get(name.lower(), None)
        if not provider:
            raise RuntimeError(
                f"Provider {name} not available. Options are {list(providers.keys())}"
            )
        return provider
    else:
        # select a default provider
        for provider in [K3dManager, KindManager, MinikubeDockerManager]:
            if not shutil.which(provider.get_binary_name()):
                continue
            return provider
        else:
            raise RuntimeError(
                "There is none of the supported Kubernetes provider installed to this system"
            )
