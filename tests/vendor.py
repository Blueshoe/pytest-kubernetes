from pathlib import Path
import subprocess

import pytest

from pytest_kubernetes.providers import select_provider_manager
from pytest_kubernetes.providers.base import AClusterManager


@pytest.fixture(scope="session")
def k8s_with_workload(request):
    cluster = select_provider_manager()("my-cluster")
    # if minikube should be used
    # cluster = select_provider_manager("minikube")("my-cluster")
    cluster.create()
    # init the cluster with a workload
    cluster.apply((Path(__file__).parent / Path("./fixtures/hello.yaml")).resolve())
    yield cluster
    cluster.delete()


def test_a_feature_with_k3d(k8s: AClusterManager):
    assert k8s.get_binary_name() == "k3d"
    k8s.create()


def test_b_cluster_deleted():
    process = subprocess.run(
        ["docker", "ps", "--format", '\'{"Names":"{{ .Names }}"}\''],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    assert "k3d-pytest-kubernetes-plugin" not in process.stdout


@pytest.mark.k8s(keep=True)
def test_c_keep_k3d(k8s: AClusterManager):
    assert k8s.get_binary_name() == "k3d"
    k8s.create()
    k8s.apply(
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "data": {"key": "value"},
            "metadata": {"name": "myconfigmap"},
        },
    )
    k8s.apply((Path(__file__).parent / Path("./fixtures/hello.yaml")).resolve())


@pytest.mark.k8s(keep=True)
def test_d_kept_cluster_delete(k8s: AClusterManager):
    process = subprocess.run(
        ["docker", "ps", "--format", '\'{"Names":"{{ .Names }}"}\''],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    assert "k3d-pytest-kubernetes-plugin" in process.stdout

    configmap = k8s.kubectl(["get", "configmap", "myconfigmap"])
    assert len(configmap["data"].keys()) == 1
    assert configmap["data"]["key"] == "value"
    assert configmap["metadata"]["uid"] is not None


def test_e_kept_cluster_delete(k8s: AClusterManager):
    process = subprocess.run(
        ["docker", "ps", "--format", '\'{"Names":"{{ .Names }}"}\''],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    assert "k3d-pytest-kubernetes-plugin" in process.stdout

    configmap = k8s.kubectl(["get", "configmap", "myconfigmap"])
    assert len(configmap["data"].keys()) == 1
    assert configmap["data"]["key"] == "value"
    assert configmap["metadata"]["uid"] is not None

    k8s.reset()
    with pytest.raises(subprocess.CalledProcessError):
        configmap = k8s.kubectl(["get", "configmap", "myconfigmap"])

    k8s.delete()
    process = subprocess.run(
        ["docker", "ps", "--format", '\'{"Names":"{{ .Names }}"}\''],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    assert "k3d-pytest-kubernetes-plugin" not in process.stdout


def test_f_prepopulated_cluster(k8s_with_workload: AClusterManager):
    k8s = k8s_with_workload

    deployment = k8s.kubectl(["get", "deployment", "hello-nginxdemo"])
    assert deployment["metadata"]["uid"] is not None

    process = subprocess.run(
        ["docker", "ps", "--format", '\'{"Names":"{{ .Names }}"}\''],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    assert "k3d-pytest-my-cluster" in process.stdout


def test_g_prepopulated_cluster_kept(k8s_with_workload: AClusterManager):
    k8s = k8s_with_workload

    deployment = k8s.kubectl(["get", "deployment", "hello-nginxdemo"])
    assert deployment["metadata"]["uid"] is not None

    process = subprocess.run(
        ["docker", "ps", "--format", '\'{"Names":"{{ .Names }}"}\''],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    assert "k3d-pytest-my-cluster" in process.stdout
    k8s.reset()
    with pytest.raises(subprocess.CalledProcessError):
        k8s.kubectl(["get", "deployment", "hello-nginxdemo"])


@pytest.mark.k8s(provider="minikube", keep=True)
def test_z_feature_with_minikube(k8s: AClusterManager):
    assert k8s.get_binary_name() == "minikube"
    k8s.create()
    # after this test case, we want no minikube cluster remaing; assertion in test_plugin.py


@pytest.mark.k8s(keep=True)
def test_z_keep_k3d_over_testrun(k8s: AClusterManager):
    k8s.create()
    # after this test case, we want no k3d cluster remaing; assertion in test_plugin.py
