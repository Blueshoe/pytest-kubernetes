# pytest-kubernetes
pytest-kubernetes is a lightweight pytest plugin that makes managing (local) Kubernetes clusters a breeze. You can easily spin up a Kubernetes cluster with one [pytest fixure](https://docs.pytest.org/en/latest/explanation/fixtures.html) and remove them again.
The fixture comes with some simple functions to interact with the cluster, for example `kubectl(...)` that allows you to run typical *kubectl* commands against this cluster without worring 
about the *kubeconfig* on the test machine.

**Features:**
- Set up and tear down (local) Kubernetes clusters with *minikube*, *k3d* and *kind*
- Configure the cluster to recreate for each test case (default), or keep it across multiple test cases
- Automatic management of the *kubeconfig*
- Simple functions to run kubectl commands (with *dict* output), reading logs and load custom container images
- Wait for certain conditions in the cluster
- Port forward Kubernetes-based services (using kubectl port-forward) easily during a test case
- Management utils for custom pytest-fixtures (for example pre-provisioned clusters)
 
## Installation
This plugin can be installed from PyPI:
- `pip install pytest-kubernetes`
- `poetry add -D pytest-kubernetes`

Note that this package provides entrypoint hooks to be automatically loaded with pytest.

## Requirements
pytest-kubernetes expects the following components to be available on the test machine:
- [`kubectl`](https://kubernetes.io/docs/reference/kubectl/)
- [`minikube`](https://minikube.sigs.k8s.io/docs/start/) (optional for minikube-based clusters)
- [`k3d`](https://k3d.io/) (optional for k3d-based clusters)
- [`kind`](https://kind.sigs.k8s.io/) (optional for kind-based clusters)
- [Docker](https://docs.docker.com/get-docker/) (optional for Docker-based Kubernetes clusters)

Please make sure they are installed to run pytest-kubernetes properly.

## Reference

### Fixture

#### k8s
The _k8s_ fixture provides access to an automatically selected Kubernetes provider (depending on the availability on the host). The priority is: k3d, kind, minikube-docker and minikube-kvm2.

The fixture passes a manager object of type *AClusterManager*.

It provides the following interface:
- `kubectl(...)`: Execute kubectl command against this cluster (defaults to `dict` as returning format)
- `apply(...)`: Apply resources to this cluster, either from YAML file, or Python dict
- `load_image(...)`: Load a container image into this cluster
- `wait(...)`: Wait for a target and a condition
- `port_forwarding(...)`: Port forward a target
- `logs(...)`: Get the logs of a pod
- `version()`: Get the Kubernetes version of this cluster
- `create(...)`: Create this cluster (pass special cluster arguments with `options: List[str]` to the CLI command)
- `delete()`: Delete this cluster
- `reset()`: Delete this cluster (if it exists) and create it again

The interface provides proper typing and should be easy to work with.

**Example**

```python
def test_a_feature_with_k3d(k8s: AClusterManager):
    k8s.create()
    k8s.apply(
        {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "data": {"key": "value"},
            "metadata": {"name": "myconfigmap"},
        },
    )
    k8s.apply("./dependencies.yaml")
    k8s.load_image("my-container-image:latest")
    k8s.kubectl(
        [
            "run",
            "test",
            "--image",
            "my-container-image:latest",
            "--restart=Never",
            "--image-pull-policy=Never",
        ]
    )
```
This cluster will be deleted once the test case is over.

> Please note that you need to set *"--image-pull-policy=Never"* for images that you loaded into the cluster via the `k8s.load(name: str)` function (see example above).

### Marks
pytest-kubernetes uses [*pytest marks*](https://docs.pytest.org/en/7.1.x/how-to/mark.html) for specifying the cluster configuration for a test case

Currently the following settings are supported:

- *provider* (str): request a specific Kubernetes provider for the test case 
- *cluster_name* (str): request a specific cluster name
- *keep* (bool): keep the cluster across multiple test cases


**Example**
```python
@pytest.mark.k8s(provider="minikube", cluster_name="test1", keep=True)
def test_a_feature_in_minikube(k8s: AClusterManager):
    ...
```

### Utils
To write custom Kubernetes-based fixtures in your project you can make use of the following util functions.


#### `select_provider_manager`
This function returns a deriving class of *AClusterManager* that is not created and wrapped in a fixture yet.

`select_provider_manager(name: Optional[str] = None) -> Type[AClusterManager]`

The returning object gets called with the init parameters of *AClusterManager*, the `cluster_name: str`.

**Example**
```python
@pytest.fixture(scope="session")
def k8s_with_workload(request):
    cluster = select_provider_manager("k3d")("my-cluster")
    # if minikube should be used
    # cluster = select_provider_manager("minikube")("my-cluster")
    cluster.create()
    # init the cluster with a workload
    cluster.apply("./fixtures/hello.yaml")
    cluster.wait("deployments/hello-nginxdemo", "condition=Available=True")
    yield cluster
    cluster.delete()
```
In this example, the cluster remains active for the entire session and is only deleted once pytest is done.

> Note that `yield` notation that is prefered by pytest to express clean up tasks for this fixture.

#### Special cluster options
You can pass more options using `kwargs['options']: List[str]` to the `create(options=...)` function when creating the cluster like so:
```python
    cluster = select_provider_manager("k3d")("my-cluster")
    # bind ports of this k3d cluster
    cluster.create(options=["--agents", "1", "-p", "8080:80@agent:0", "-p", "31820:31820/UDP@agent:0"])
```

## Examples
Please find more examples in *tests/vendor.py* in this repository. These test cases are written as users of pytest-kubernetes would write test cases in their projects.