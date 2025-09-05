from typing import Dict, Type
import pytest
from pytest import FixtureRequest

from pytest_kubernetes.providers import select_provider_manager
from pytest_kubernetes.providers.base import AClusterManager

cluster_cache: Dict[str, Type[AClusterManager]] = {}


@pytest.fixture
def k8s(request: FixtureRequest, k8s_manager):
    """Provide a Kubernetes cluster as test fixture."""

    provider = None
    cluster_name = None
    keep = False
    provider_config = None
    external_kubeconfig = None
    if "k8s" in request.keywords:
        req = dict(request.keywords["k8s"].kwargs)
        provider = req.get("provider")
        cluster_name = req.get("cluster_name") or cluster_name
        keep = req.get("keep", False)
        provider_config = req.get("provider_config")
        external_kubeconfig = req.get("k8s_kubeconfig")
    if not provider:
        provider = request.config.getoption("k8s_provider")
    if not cluster_name:
        cluster_name = request.config.getoption("k8s_cluster_name")

    manager_klass = k8s_manager(provider)
    cache_key = f"{manager_klass.__name__}-{cluster_name}"
    # check if this provider is kept from another test function
    if cache_key in cluster_cache:
        manager = cluster_cache[cache_key]
        del cluster_cache[cache_key]
    else:
        manager: AClusterManager = manager_klass(
            cluster_name, provider_config, external_kubeconfig
        )  # type: ignore

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


@pytest.fixture
def k8s_manager(request: FixtureRequest):
    pytest_options = {
        "cluster_name": request.config.getoption("k8s_cluster_name"),
        "provider": request.config.getoption("k8s_provider"),
        "version": request.config.getoption("k8s_version"),
        "provider_config": request.config.getoption("k8s_provider_config"),
        "kubeconfig_override": request.config.getoption("k8s_kubeconfig_override"),
        "kubeconfig": request.config.getoption("k8s_kubeconfig"),
    }

    def k8s_factory(provider_name: str | None = None):
        if not provider_name:
            provider_name = pytest_options.get("provider")
        return select_provider_manager(provider_name, pytest_options)

    yield k8s_factory


def pytest_addoption(parser):
    k8s_group = parser.getgroup("k8s")
    k8s_group.addoption(
        "--k8s-cluster-name",
        default="pytest",
        help="Name of the Kubernetes cluster (default 'pytest').",
    )
    k8s_group.addoption(
        "--k8s-provider",
        help="The default cluster provider; selects k3d, kind, minikube, external depending on what is available",
    )
    k8s_group.addoption(
        "--k8s-version",
        help="The default cluster provider; selects k3d, kind, minikube depending on what is available",
    )
    k8s_group.addoption(
        "--k8s-provider-config",
        help="Path to a Provider cluster config file",
    )
    k8s_group.addoption(
        "--k8s-kubeconfig-override",
        help="Path to a kubeconfig of a cluster not created by pytest-kubernetes; overrides test configs",
    )
    k8s_group.addoption(
        "--k8s-kubeconfig",
        help="Path to a kubeconfig of a cluster not created by pytest-kubernetes",
    )


def pytest_configure(config: pytest.Config):
    cluster_name = config.getoption("k8s_cluster_name")
    provider = config.getoption("k8s_provider")
    provider_config = config.getoption("k8s_provider_config")
    external_kubeconfig = config.getoption("k8s_kubeconfig")
    external_kubeconfig_override = config.getoption("k8s_kubeconfig_override")
    available_providers = [
        "k3d",
        "kind",
        "minikube",
        "minikube-docker",
        "minikube-kvm2",
        "external",
    ]

    if cluster_name and provider_config:
        raise pytest.UsageError(
            "Cannot specify both --k8s-cluster-name and --k8s-provider-config"
        )
    if (provider_config and external_kubeconfig) or (
        provider_config and external_kubeconfig_override
    ):
        raise pytest.UsageError(
            "Cannot specify both --k8s-provider-config and --k8s-kubeconfig[-override]"
        )
    if provider and provider.lower() not in available_providers:
        raise pytest.UsageError(
            f"Provider '{provider}' not available in {available_providers}"
        )
    if (
        provider
        and provider.lower() == "external"
        and (not external_kubeconfig and not external_kubeconfig_override)
    ):
        raise pytest.UsageError(
            "Cannot request 'external' provider without --k8s-kubeconfig[-override]"
        )
