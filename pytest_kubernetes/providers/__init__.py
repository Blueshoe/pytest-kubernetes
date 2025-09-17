import shutil, sys, argparse
from typing import Type
from pytest_kubernetes.options import ClusterOptions
from pytest_kubernetes.providers.base import AClusterManager
from .k3d import K3dManagerBase
from .kind import KindManagerBase
from .minikube import MinikubeDockerManagerBase, MinikubeKVM2ManagerBase
from .external import ExternalManagerBase


K3D = "k3d"
KIND = "kind"
MINIKUBE = "minikube"
MINIKUBE_DOCKER = "minikube-docker"
MINIKUBE_KVM = "minikube-kvm2"
EXTERNAL = "external"


def select_provider_manager(
    name: str | None = None, pytest_options: dict | None = None
) -> Type[AClusterManager]:
    kubeconfig = None
    cluster_options = ClusterOptions()
    default_provider = None

    if pytest_options and name and name.lower() == EXTERNAL:
        kubeconfig = pytest_options.get("kubeconfig")

    if not name and pytest_options and pytest_options.get("kubeconfig"):
        default_provider = EXTERNAL
        kubeconfig = pytest_options.get("kubeconfig")

    if pytest_options and pytest_options.get("kubeconfig_override"):
        default_provider = EXTERNAL
        kubeconfig = pytest_options.get("kubeconfig_override")

    if not name and pytest_options and pytest_options.get("provider"):
        name = pytest_options.get("provider")

    # init with defaults from pytest args
    if pytest_options and pytest_options.get("cluster_name"):
        cluster_options.cluster_name = pytest_options.get("cluster_name")
    if pytest_options and pytest_options.get("version"):
        cluster_options.version = pytest_options.get("version")

    if not name and default_provider:
        name = default_provider

    providers = {
        K3D: type(
            "K3dManager", (K3dManagerBase,), {"_cluster_options": cluster_options}
        ),
        KIND: type(
            "KindManager", (KindManagerBase,), {"_cluster_options": cluster_options}
        ),
        MINIKUBE: type(
            "MinikubeDockerManager",
            (MinikubeDockerManagerBase,),
            {"_cluster_options": cluster_options},
        ),
        MINIKUBE_DOCKER: type(
            "MinikubeDockerManager",
            (MinikubeDockerManagerBase,),
            {"_cluster_options": cluster_options},
        ),
        MINIKUBE_KVM: type(
            "MinikubeKVM2Manager",
            (MinikubeKVM2ManagerBase,),
            {"_cluster_options": cluster_options},
        ),
        EXTERNAL: type(
            "ExternalManager", (ExternalManagerBase,), {"_kubeconfig": kubeconfig}
        ),
    }

    if name:
        provider = providers.get(name.lower(), None)
        if not provider:
            raise RuntimeError(
                f"Provider {name} not available. Options are {list(providers.keys())}"
            )
        return provider
    else:
        # select a default provider
        for provider in [
            providers.get(K3D),
            providers.get(KIND),
            providers.get(MINIKUBE_DOCKER),
        ]:
            if not shutil.which(provider.get_binary_name()):
                continue
            return provider
        else:
            raise RuntimeError(
                "There is none of the supported Kubernetes provider installed to this system"
            )
