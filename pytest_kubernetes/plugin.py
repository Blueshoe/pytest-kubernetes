from typing import Dict, Type
import pytest

from pytest_kubernetes.providers import select_provider_manager
from pytest_kubernetes.providers.base import AClusterManager

cluster_cache: Dict[str, Type[AClusterManager]] = {}


@pytest.fixture
def k8s(request):
    """Provide a Kubernetes cluster as test fixture."""

    provider = None
    cluster_name = None
    keep = False
    if "k8s" in request.keywords:
        req = dict(request.keywords["k8s"].kwargs)
        provider = req.get("provider")
        cluster_name = req.get("cluster_name") or cluster_name
        keep = req.get("keep")
    if not provider:
        provider = provider = request.config.getoption("k8s_provider")
    if not cluster_name:
        cluster_name = request.config.getoption("k8s_cluster_name")

    manager_klass = select_provider_manager(provider)
    cache_key = f"{manager_klass.__name__}-{cluster_name}"
    # check if this provider is kept from another test function
    if cache_key in cluster_cache:
        manager = cluster_cache[cache_key]
        del cluster_cache[cache_key]
    else:
        manager: AClusterManager = manager_klass(cluster_name)

    def delete_cluster():
        manager.delete()

    if not keep:
        request.addfinalizer(delete_cluster)
    else:
        # if this cluster is to be kept put it to cache
        cluster_cache[cache_key] = manager
    return manager


@pytest.fixture(scope="session", autouse=True)
def remaining_clusters_teardown():
    yield
    for _, cluster in cluster_cache.items():
        cluster.delete()


def pytest_addoption(parser):
    group = parser.getgroup("k8s")
    group.addoption(
        "--k8s-cluster-name",
        default="pytest",
        help="Name of the Kubernetes cluster (default 'pytest').",
    )
    group.addoption(
        "--k8s-provider",
        help="The default cluster provider; selects k3d, kind, minikube depending on what is available",
    )
    group.addoption(
        "--k8s-version",
        help="The default cluster provider; selects k3d, kind, minikube depending on what is available",
    )
