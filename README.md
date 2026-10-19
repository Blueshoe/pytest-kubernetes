# pytest-kubernetes

> **Stop mocking Kubernetes. Mocks don't have crash loops, OOM kills, DNS gremlins, or angry admission webhooks. Test against the real thing.**

`pytest-kubernetes` is a lightweight pytest plugin that makes orchestrating local Kubernetes clusters in your tests an absolute breeze. With a single pytest fixture, you can spin up an authentic, fire-breathing Kubernetes cluster, test your workloads, run queries with parsed JSON returns, forward ports, and banish the cluster into the void when your tests are done.

No 500-line Makefile hacks. No bash glue scripts. Just Python, pytest, and pure Kubernetes bliss.

---

## ⚡ Features That Will Save Your Sanity

- 🚀 **Multi-Provider Magic:** Seamlessly orchestrate **k3d**, **kind**, and **minikube** (Docker & KVM2 drivers) without changing a single line of test code.
- 🛸 **External Cluster Support:** Connect your tests to an already-running local or remote cluster without letting pytest accidentally obliterate it.
- ♻️ **Ephemeral or Persistent:** Nuke & pave a fresh cluster per test, or use `keep=True` to preserve clusters across test runs so your laptop's cooling fan doesn't try to achieve orbit.
- 🧘 **Auto-Managed Kubeconfigs:** Never leak test contexts into your personal `~/.kube/config` again. Everything runs isolated in ephemeral configs.
- 🐍 **Pythonic `kubectl`:** `k8s.kubectl(["get", "pods"])` returns a native Python `dict` by default. No more `awk '{print $1}'` regex horror in your test assertions.
- 📦 **Effortless `apply()`:** Apply manifests from YAML files *or* directly from raw Python dictionaries.
- 🚢 **Image Side-Loading:** Push local Docker images straight into your cluster nodes without begging Docker Hub not to rate-limit you into oblivion.
- 🔌 **Context-Managed Port-Forwarding:** Forward ports from pods or services straight to localhost with clean `with k8s.port_forwarding(...)` blocks.
- ⏱️ **Built-in `wait()` & `logs()`:** Wait for conditions and fetch namespace-aware container logs without breaking a sweat.

---

## 📦 Installation

Install directly from PyPI via `pip` or `poetry`:

```bash
# Using pip
pip install pytest-kubernetes

# Using poetry
poetry add --group dev pytest-kubernetes
```

The plugin registers entrypoint hooks with pytest automatically. You don't need to configure `conftest.py` with custom hooks—just install and write tests!

---

## 🛠️ Prerequisites

`pytest-kubernetes` relies on your favorite cluster provider CLI. You only need the tool(s) you plan to use:

- [`kubectl`](https://kubernetes.io/docs/reference/kubectl/) *(Required)*
- [`k3d`](https://k3d.io/) *(Optional, for lightweight k3s clusters in Docker)*
- [`kind`](https://kind.sigs.k8s.io/) *(Optional, for Kubernetes-in-Docker)*
- [`minikube`](https://minikube.sigs.k8s.io/) *(Optional, Docker or KVM2 drivers)*
- [Docker](https://docs.docker.com/get-docker/) *(Required for Docker-based providers)*

If you don't specify a provider, `pytest-kubernetes` automatically picks the first available provider on your machine (priority: `k3d` ➔ `kind` ➔ `minikube-docker` ➔ `minikube-kvm2`).

---

## 🏎️ Quickstart

Spinning up a cluster, applying a workload, and verifying that it actually works:

```python
from pathlib import Path
from pytest_kubernetes.providers import AClusterManager


def test_my_kubernetes_app(k8s: AClusterManager):
    # 1. Spin up the cluster (auto-detected provider: k3d, kind, or minikube)
    k8s.create()

    # 2. Apply a manifest from a Python dictionary (no disk I/O required!)
    k8s.apply(
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {"name": "app-config"},
            "data": {"API_URL": "https://api.awesome.local"},
        }
    )

    # 3. Apply manifests from YAML files
    k8s.apply(Path("./tests/fixtures/hello-nginx.yaml"))

    # 4. Wait for your deployment to become ready
    k8s.wait("deployments/hello-nginxdemo", "condition=Available=True", timeout=60)

    # 5. Query cluster state with native Python dictionaries!
    data = k8s.kubectl(["get", "deployments", "-o", "json"])
    assert data["items"][0]["metadata"]["name"] == "hello-nginxdemo"

    # 6. Check logs
    logs = k8s.logs(pod="hello-nginxdemo-xxx", container="nginx", namespace="default")
    assert "ready for start up" in logs
```

Once the test finishes, `pytest-kubernetes` tears down the cluster and unlinks temporary kubeconfigs automatically. Neat and clean.

---

## 🧰 The Toolbelt: `AClusterManager` Interface

The `k8s` fixture hands you an instance of `AClusterManager` packed with superpowers:

| Method | Description |
| :--- | :--- |
| `k8s.create(cluster_options=None, timeout=20, **kwargs)` | Spawns the cluster and waits until `/readyz` passes and the `default` service account is ready. |
| `k8s.delete()` | Safely obliterates the cluster and cleans up its temporary kubeconfig. |
| `k8s.reset()` | Deletes the cluster and starts a squeaky clean one from scratch. |
| `k8s.kubectl(args, as_dict=True, timeout=60)` | Runs `kubectl` commands. Returns a parsed Python `dict` if `as_dict=True` (default), or raw `str` if `as_dict=False`. |
| `k8s.apply(input)` | Deploys resources from a file path (`str` or `Path`) or a Python `dict`. |
| `k8s.load_image(image_name)` | Side-loads a local Docker image into the cluster. |
| `k8s.port_forwarding(target, port_a, port_b, namespace="default")` | Returns a `PortForwarding` object supporting context manager (`with`) syntax. |
| `k8s.wait(target, condition, timeout=30)` | Executes `kubectl wait --for=<condition>` against a resource. |
| `k8s.logs(pod, container=None, namespace=None)` | Fetches logs for a pod/container without raw shell escaping. |
| `k8s.version()` | Returns the cluster's Kubernetes server version as a `(major, minor)` tuple (e.g. `(1, 28)`). |
| `k8s.ready(timeout=20)` | Checks if the cluster is healthy and ready to accept workloads. |
| `k8s.kubeconfig` | `Path` pointing to the isolated kubeconfig file for this cluster. |

### 🔍 Tip 1: No More String Parsing with `kubectl`
```python
# Returns a Python dictionary parsed from JSON!
pods = k8s.kubectl(["get", "pods", "-n", "kube-system"])
for pod in pods["items"]:
    print(pod["metadata"]["name"], pod["status"]["phase"])

# Want raw text output instead? Easy:
raw_output = k8s.kubectl(["get", "nodes"], as_dict=False)
assert "control-plane" in raw_output
```

### 🔌 Tip 2: Seamless Port-Forwarding in Tests
Don't worry about lingering background processes. Use Python's `with` statement:

```python
import urllib.request


def test_service_endpoint(k8s: AClusterManager):
    k8s.create()
    k8s.apply("./manifests/nginx.yaml")
    k8s.wait("deployments/nginx", "condition=Available=True")

    # Forward localhost:8080 to service port 80
    with k8s.port_forwarding("svc/nginx-service", 8080, 80):
        response = urllib.request.urlopen("http://127.0.0.1:8080", timeout=5)
        assert response.status == 200
    # Port forward is stopped automatically when exiting the block!
```

### 🚢 Tip 3: Testing Locally Built Docker Images
Avoid pushing your private build images to public registries just to run a test:

```python
def test_local_docker_build(k8s: AClusterManager):
    k8s.create()

    # Load local docker image into k3d, kind, or minikube node(s)
    k8s.load_image("my-custom-app:v1.0.0")

    # Important: set imagePullPolicy: Never so k8s uses the loaded image
    k8s.apply(
        {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "app-test"},
            "spec": {
                "containers": [
                    {
                        "name": "app",
                        "image": "my-custom-app:v1.0.0",
                        "imagePullPolicy": "Never",
                    }
                ]
            },
        }
    )
```

---

## 🏷️ Test Marks: Tailoring Clusters Per Test

Using the `@pytest.mark.k8s` marker, you can declaratively customize the cluster for specific test cases:

```python
import pytest
from pytest_kubernetes.providers import AClusterManager


# Test against a specific provider with a custom name
@pytest.mark.k8s(provider="kind", cluster_name="ci-kind-test")
def test_specifically_on_kind(k8s: AClusterManager):
    assert k8s.get_binary_name() == "kind"
    k8s.create()


# Keep the cluster alive for subsequent tests to reuse!
@pytest.mark.k8s(provider="k3d", keep=True)
def test_seed_cluster(k8s: AClusterManager):
    k8s.create()
    k8s.apply("./fixtures/base-db.yaml")


@pytest.mark.k8s(provider="k3d", keep=True)
def test_read_seeded_data(k8s: AClusterManager):
    # Cluster is already running with base-db from previous test!
    config = k8s.kubectl(["get", "services"])
    assert len(config["items"]) > 0
```

### Supported Marker Arguments:
- `provider` (`str`): Select `"k3d"`, `"kind"`, `"minikube"`, `"minikube-docker"`, `"minikube-kvm2"`, or `"external"`.
- `cluster_name` (`str`): Specify a custom name for the cluster.
- `keep` (`bool`): Keep the cluster alive across test cases instead of tearing it down immediately.
- `provider_config` (`str` | `Path`): Path to a provider configuration file.
- `k8s_kubeconfig` (`str` | `Path`): Path to an existing cluster's kubeconfig for the `"external"` provider.

---

## 🛠️ Custom Provider Configurations

Want to mount custom host volumes, forward cluster agent ports, or configure multi-node clusters? Pass your provider's native configuration file using `ClusterOptions`:

```python
from pathlib import Path
from pytest_kubernetes.options import ClusterOptions
from pytest_kubernetes.providers import AClusterManager


def test_custom_topology(k8s: AClusterManager):
    # Pass a provider config file directly to create()
    k8s.create(
        cluster_options=ClusterOptions(
            provider_config=Path("./tests/fixtures/k3d_config.yaml")
        )
    )
```

You can also pass raw provider CLI arguments with `options`:

```python
def test_with_custom_flags(k8s: AClusterManager):
    k8s.create(
        options=[
            "--agents",
            "2",
            "-p",
            "8080:80@agent:0",
            "--agents-memory",
            "4G",
        ]
    )
```

Native config documentation by provider:
- **kind:** [kind Cluster Configuration](https://kind.sigs.k8s.io/docs/user/configuration/)
- **k3d:** [k3d Configuration File](https://k3d.io/v5.1.0/usage/configfile/)
- **minikube:** Uses standard YAML matching minikube configuration properties (see [mk_config.yaml](https://github.com/Blueshoe/pytest-kubernetes/blob/main/tests/fixtures/mk_config.yaml)).

---

## 🏭 Custom Fixtures with `k8s_manager`

When building complex test suites, you often need module-scoped or session-scoped clusters pre-loaded with infrastructure (e.g. operators, CRDs, databases).

The `k8s_manager` fixture acts as a cluster factory:

```python
import os
import pytest
from pytest_kubernetes.providers import AClusterManager


@pytest.fixture(scope="module")
def prepared_cluster(k8s_manager):
    # Obtain a manager instance for k3d
    cluster: AClusterManager = k8s_manager("k3d")("analytics-cluster")

    # Check if cluster is already alive, otherwise create it
    if not cluster.ready(timeout=2):
        cluster.create()
        cluster.apply("./manifests/crds.yaml")
        cluster.apply("./manifests/database.yaml")
        cluster.wait(
            "deployments/database", "condition=Available=True", timeout=120
        )

    # Expose kubeconfig to application libraries via environment
    os.environ["KUBECONFIG"] = str(cluster.kubeconfig)

    yield cluster

    # Tear down after module tests finish
    cluster.delete()
```

---

## 💻 CLI Flags: Command Your Tests from the Terminal

Run tests without modifying any code using pytest command line arguments:

```bash
# Force tests to use kind
pytest --k8s-provider kind

# Request a specific Kubernetes version
pytest --k8s-version 1.30.0

# Provide a custom cluster config file
pytest --k8s-provider-config ./ci/kind-multi-node.yaml

# Set a custom cluster name prefix
pytest --k8s-cluster-name my-test-runner
```

### ☕ The "Save My CPU" Override Flag
Running a huge test suite locally and tired of waiting for clusters to spin up and tear down?
Point your entire test suite at an already-running cluster with `--k8s-kubeconfig-override`:

```bash
# 1. Spin up a cluster once manually
k3d cluster create dev-cluster
k3d kubeconfig get dev-cluster > /tmp/dev-kubeconfig.yaml

# 2. Run your tests in lightning speed against the existing cluster
pytest --k8s-kubeconfig-override /tmp/dev-kubeconfig.yaml -v
```

When `--k8s-kubeconfig-override` is passed, `pytest-kubernetes` automatically switches to the `external` provider, runs against your existing cluster, and **leaves it untouched** when tests complete. Go grab a coffee with all the time you saved.

---

## 🧪 Real-World Example

Check out `tests/vendor.py` in this repository to see how real-world projects (such as [Gefyra](https://github.com/gefyrahq/gefyra)) use `pytest-kubernetes` in production CI/CD pipelines!

---

## 🤝 Contributing

Contributions, bug reports, and witty pull requests are warmly welcome!
1. Fork the repo and create your branch.
2. Install dependencies with `poetry install`.
3. Run linters and tests:
   ```bash
   poetry run ruff check .
   poetry run mypy pytest_kubernetes
   poetry run pytest -v
   ```
4. Submit your PR and bask in the glory.

---

## 📄 License

Licensed under the Apache-2.0 License. See [LICENSE](LICENSE) for details.
