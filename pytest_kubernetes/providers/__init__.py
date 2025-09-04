import shutil, sys, argparse
from typing import Type
from pytest_kubernetes.providers.base import AClusterManager
from .k3d import K3dManagerBase
from .kind import KindManager
from .minikube import MinikubeDockerManager, MinikubeKVM2Manager
from .external import ExternalManagerBase


def select_provider_manager(
    name: str | None = None, pytest_options: dict | None = None
) -> Type[AClusterManager]:
    kubeconfig = None
    cluster_name = ""

    if pytest_options and name and name.lower() == "external":
        kubeconfig = pytest_options.get("kubeconfig")

    if not name and pytest_options and pytest_options.get("kubeconfig"):
        name = "external"
        kubeconfig = pytest_options.get("kubeconfig")

    if pytest_options and pytest_options.get("kubeconfig_override"):
        name = "external"
        kubeconfig = pytest_options.get("kubeconfig_override")

    if pytest_options and pytest_options.get("cluster_name"):
        cluster_name = pytest_options.get("cluster_name")

    if name:
        providers = {
            "k3d": type(
                "K3dManager", (K3dManagerBase,), {"cluster_name": cluster_name}
            ),
            "kind": KindManager,
            "minikube": MinikubeDockerManager,
            "minikube-docker": MinikubeDockerManager,
            "minikube-kvm2": MinikubeKVM2Manager,
            "external": type(
                "ExternalManager", (ExternalManagerBase,), {"_kubeconfig": kubeconfig}
            ),
        }
        provider = providers.get(name.lower(), None)
        if not provider:
            raise RuntimeError(
                f"Provider {name} not available. Options are {list(providers.keys())}"
            )
        return provider
    else:
        # select a default provider
        for provider in [K3dManagerBase, KindManager, MinikubeDockerManager]:
            if not shutil.which(provider.get_binary_name()):
                continue
            return provider
        else:
            raise RuntimeError(
                "There is none of the supported Kubernetes provider installed to this system"
            )
