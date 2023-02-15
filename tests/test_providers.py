from pathlib import Path
from time import sleep
from typing import Type

import pytest

from pytest_kubernetes.providers.base import AClusterManager
from pytest_kubernetes.providers import *


class KubernetesManagerTest:
    manager: Type[AClusterManager] = None
    cluster: AClusterManager = None
    cluster_name = "pytest"

    def test_a_create_simple_cluster(self):
        self.cluster.create()
        output = self.cluster.kubectl(["get", "nodes"], as_dict=False)
        assert self.cluster.cluster_name in output
        assert "control-plane" in output
        data = self.cluster.kubectl(["get", "nodes"])
        assert len(data["items"]) == 1
        assert self.cluster.kubeconfig is not None
        # assert server version
        assert (1, 25) == self.cluster.version()

    def test_b_reset_cluster(self):
        self.cluster = self.manager(self.cluster_name)
        self.cluster.reset()

    def test_c_apply_yaml_file(self):
        self.cluster.create()
        self.cluster.apply(
            (Path(__file__).parent / Path("./fixtures/hello.yaml")).resolve()
        )
        data = self.cluster.kubectl(["get", "deployments"])
        assert len(data["items"]) == 1
        assert data["items"][0]["metadata"]["name"] == "hello-nginxdemo"

    def test_c_apply_data(self):
        self.cluster.create()
        # apply a configmap from dict
        self.cluster.apply(
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "data": {"key": "value"},
                "metadata": {"name": "myconfigmap"},
            },
        )
        configmap = self.cluster.kubectl(["get", "configmap", "myconfigmap"])
        assert len(configmap["data"].keys()) == 1
        assert configmap["data"]["key"] == "value"
        assert configmap["metadata"]["uid"] is not None

    def test_e_load_image_read_logs(self, a_unique_image):
        self.cluster.create()
        self.cluster.load_image(a_unique_image)
        self.cluster.kubectl(
            [
                "run",
                "test",
                "--image",
                a_unique_image,
                "--restart=Never",
                "--image-pull-policy=Never",
            ]
        )
        _i = 0
        exception = None
        while _i < 30:
            sleep(1)
            try:
                pod = self.cluster.kubectl(["get", "pod", "test"])
                assert pod["spec"]["containers"][0]["image"] == a_unique_image
                assert pod["status"]["phase"] == "Succeeded"
                assert "hello world" in self.cluster.logs(pod="test", container="test")
                break
            except (AssertionError, KeyError) as e:
                _i += 1
                exception = e
                continue
        else:
            raise exception

    def teardown_method(self, method):
        self.cluster.delete()

    def setup_method(self, method):
        self.cluster = self.manager(self.cluster_name)


class Testk3d(KubernetesManagerTest):
    manager = K3dManager


class Testkind(KubernetesManagerTest):
    manager = KindManager


class TestDockerminikube(KubernetesManagerTest):
    manager = MinikubeDockerManager


class TestKVM2minikube(KubernetesManagerTest):
    manager = MinikubeKVM2Manager


def test_select_provider(monkeypatch):
    provider_klass = select_provider_manager()
    assert issubclass(provider_klass, AClusterManager)

    k3d_klass = select_provider_manager("k3d")
    assert k3d_klass == K3dManager
    minikube_klass = select_provider_manager("minikube")
    assert minikube_klass == MinikubeDockerManager
    minikube_klass = select_provider_manager("minikube-docker")
    assert minikube_klass == MinikubeDockerManager
    minikube_klass = select_provider_manager("minikube-kvm2")
    assert minikube_klass == MinikubeKVM2Manager
    # if k3d is not available
    monkeypatch.setattr(K3dManager, "get_binary_name", lambda: "k3dlol")
    provider_klass = select_provider_manager()
    assert provider_klass != K3dManager

    with pytest.raises(RuntimeError):
        _ = select_provider_manager("rofl")
