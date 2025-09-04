from pathlib import Path
from time import sleep
from typing import Type

import pytest

from pytest_kubernetes.options import ClusterOptions
from pytest_kubernetes.providers import (
    AClusterManager,
    K3dManagerBase,
    KindManager,
    MinikubeDockerManager,
    MinikubeKVM2Manager,
    select_provider_manager,
)
from pytest_kubernetes.providers.external import ExternalManagerBase


class KubernetesManagerTest:
    manager: Type[AClusterManager] | None = None
    cluster: AClusterManager | None = None
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
        self.cluster.create()
        self.cluster.kubectl(["get", "nodes"])
        kubeconfig1 = self.cluster.kubeconfig
        self.cluster.reset()
        kubeconfig2 = self.cluster.kubeconfig
        self.cluster.kubectl(["get", "nodes"])
        assert kubeconfig1 != kubeconfig2

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

    def test_f_portforwarding(self):
        import urllib.request

        self.cluster.create()
        self.cluster.apply(
            (Path(__file__).parent / Path("./fixtures/hello.yaml")).resolve()
        )
        self.cluster.wait("deployments/hello-nginxdemo", "condition=Available=True")
        forwarding_nginx = self.cluster.port_forwarding("svc/hello-nginx", 9090, 80)
        with forwarding_nginx:
            response = urllib.request.urlopen("http://127.0.0.1:9090", timeout=20)
            assert response.status == 200

        forwarding_nginx = self.cluster.port_forwarding("svc/hello-nginx", 9090, 80)
        forwarding_nginx.start()
        response = urllib.request.urlopen("http://127.0.0.1:9090", timeout=20)
        assert response.status == 200
        forwarding_nginx.stop()

    def test_d_logs_namespace(self):
        self.cluster.create()
        self.cluster.apply(
            (Path(__file__).parent / Path("./fixtures/hello.yaml")).resolve()
        )
        self.cluster.wait("deployments/hello-nginxdemo", "condition=Available=True")

        data = self.cluster.kubectl(["get", "deployments", "-n", "commands"])
        assert len(data["items"]) == 1
        assert data["items"][0]["metadata"]["name"] == "hello-nginxdemo-command"

        pod_name = self.cluster.kubectl(
            [
                "get",
                "pod",
                "-n",
                "commands",
                "-o",
                "jsonpath={.items[0].metadata.name}",
            ],
            as_dict=False,
        )
        assert pod_name

        _i = 0
        exception = None
        while _i < 30:
            sleep(1)
            try:
                assert 'using the "epoll" event method' in self.cluster.logs(
                    pod=pod_name, namespace="commands"
                )
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
    manager = K3dManagerBase

    def test_custom_cluster_config(self):
        self.cluster.create(
            cluster_options=ClusterOptions(
                provider_config=Path(__file__).parent
                / Path("./fixtures/k3d_config.yaml"),
            )
        )
        cluster_name = self.cluster.kubectl(
            ["config", "view", "--minify", "-o", "jsonpath='{.clusters[].name}'"],
            as_dict=False,
        )
        assert cluster_name == "k3d-pytest-k3d-cluster"


class Testkind(KubernetesManagerTest):
    manager = KindManager

    def test_custom_cluster_config(self):
        self.cluster.create(
            cluster_options=ClusterOptions(
                provider_config=Path(__file__).parent
                / Path("./fixtures/kind_config.yaml"),
            )
        )
        cluster_name = self.cluster.kubectl(
            ["config", "view", "--minify", "-o", "jsonpath='{.clusters[].name}'"],
            as_dict=False,
        )
        assert cluster_name == "kind-pytest-kind-cluster"


class TestDockerminikube(KubernetesManagerTest):
    manager = MinikubeDockerManager

    def test_custom_cluster_config(self):
        self.cluster.create(
            cluster_options=ClusterOptions(
                provider_config=Path(__file__).parent
                / Path("./fixtures/mk_config.yaml"),
            )
        )
        cluster_name = self.cluster.kubectl(
            ["config", "view", "--minify", "-o", "jsonpath='{.clusters[].name}'"],
            as_dict=False,
        )
        assert cluster_name == "pytest-mk-cluster"


class TestKVM2minikube(KubernetesManagerTest):
    manager = MinikubeKVM2Manager


class TestExternal(KubernetesManagerTest):
    manager = ExternalManagerBase

    def setup_method(self, method):
        # create an external cluster, locally
        k3d = select_provider_manager("k3d")("pytest-external")
        k3d.create()
        k3d.kubeconfig
        self.cluster = self.manager("pytest-external", str(k3d.kubeconfig))

    def teardown_method(self, method):
        k3d = select_provider_manager("k3d")("pytest-external")
        k3d.delete()


def test_k8s_manager(k8s_manager):
    my_provider: AClusterManager = k8s_manager()
    print(my_provider)
    provider = my_provider()
    print(provider.cluster_name)
    print(provider.kubeconfig)


def test_select_provider(monkeypatch):
    provider_klass = select_provider_manager()
    assert issubclass(provider_klass, AClusterManager)

    k3d_klass = select_provider_manager("k3d")
    assert k3d_klass == K3dManagerBase
    minikube_klass = select_provider_manager("minikube")
    assert minikube_klass == MinikubeDockerManager
    minikube_klass = select_provider_manager("minikube-docker")
    assert minikube_klass == MinikubeDockerManager
    minikube_klass = select_provider_manager("minikube-kvm2")
    assert minikube_klass == MinikubeKVM2Manager
    # if k3d is not available
    monkeypatch.setattr(K3dManagerBase, "get_binary_name", lambda: "k3dlol")
    provider_klass = select_provider_manager()
    assert provider_klass != K3dManagerBase

    with pytest.raises(RuntimeError):
        _ = select_provider_manager("rofl")
