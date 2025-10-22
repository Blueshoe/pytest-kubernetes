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

#### k8s_manager
The _k8s_manager_ fixture provides a convenient factory method, similar to the util `select_provider_manager` (see below) to construct prepared Kubernetes clusters.

`k8s_manager(name: Optional[str] = None) -> Type[AClusterManager]`

In contrast to `select_provider_manager`, `k8s_manager` is sensitive to pytest-arguments from the command line or
configuration file. It allows to override the standard configuration via the `--k8s-kubeconfig-override` argument
to use an external cluster for this test run. It makes development a breeze.

**Example**

The following recipe does the following:
1) Check if the cluster is already running (created outside, for example via `k3d cluster create --config k3d_cluster.yaml`)
2) Creates a `k3d` cluster, if it's not running
3) Prepares a namespace, purge existing objects if present
4) Yields the fixture to the test case, or subrequest fixture
5) Purges objects if cluster was not created during this test run; deletes cluster in case it was created

This is used in [Gefyra](https://github.com/gefyrahq/gefyra/).


```python
@pytest.fixture(scope="module")
def k3d(k8s_manager):
    k8s: AClusterManager = k8s_manager("k3d")("gefyra")
    # ClusterOptions() forces pytest-kubernetes to always write a new kubeconfig file to disk
    cluster_exists = k8s.ready(timeout=1)
    if not cluster_exists:
        k8s.create(
            ClusterOptions(api_version="1.29.5"),
            options=[
                "--agents",
                "1",
                "-p",
                "8080:80@agent:0",
                "-p",
                "31820:31820/UDP@agent:0",
                "--agents-memory",
                "8G",
            ],
        )
    if "gefyra" not in k8s.kubectl(["get", "ns"], as_dict=False):
        k8s.kubectl(["create", "ns", "gefyra"])
        k8s.wait("ns/gefyra", "jsonpath='{.status.phase}'=Active")
    else:
        purge_gefyra_objects(k8s)
    os.environ["KUBECONFIG"] = str(k8s.kubeconfig)
    yield k8s
    if cluster_exists:
        # delete existing bridges
        purge_gefyra_objects(k8s)
        k8s.kubectl(["delete", "ns", "gefyra"], as_dict=False)
    else:
        # we delete this cluster only when created during this run
        k8s.delete()
```

This example allows to run test cases against an automatic ephemeral cluster, and a "long-living" cluster.

To run local tests without losing time in the set up and tear down of the cluster, you can follow these steps:
1) Create a local `k3d` cluster, for example from a config file: `k3d cluster create --config k3d_cluster.yaml`
2) Write the kubeconfig to file: `k3d kubeconfig get gefyra > mycluster.yaml`
3) Run the tests with an override: `pytest --k8s-kubeconfig-override mycluster.yaml --k8s-cluster-name gefyra --k8s-provider k3d -s -x tests/`

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
**Remark:** Don not use this, if you can use the fixture `k8s_manager` instead (see above).

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

#### Cluster configs
You can pass a cluster config file in the create method of a cluster:
```python
    cluster = select_provider_manager("k3d")("my-cluster")
    # bind ports of this k3d cluster
    cluster.create(
        cluster_options=ClusterOptions(
            cluster_config=Path("my_cluster_config.yaml")
        )
    )
```
For the different providers you have to submit different kinds of configuration files.
- kind: https://kind.sigs.k8s.io/docs/user/configuration/#getting-started
- k3d: https://k3d.io/v5.1.0/usage/configfile/
- minikube: Has to be a custom yaml file that corresponds to the `minikube config` command. An example can be found in the [fixtures directory](https://github.com/Blueshoe/pytest-kubernetes/tree/main/tests/fixtures/mk_config.yaml) of this repository.


#### Special cluster options
You can pass more options using `kwargs['options']: List[str]` to the `create(options=...)` function when creating the cluster like so:
```python
    cluster = select_provider_manager("k3d")("my-cluster")
    # bind ports of this k3d cluster
    cluster.create(options=["--agents", "1", "-p", "8080:80@agent:0", "-p", "31820:31820/UDP@agent:0"])
```


## Examples
Please find more examples in *tests/vendor.py* in this repository. These test cases are written as users of pytest-kubernetes would write test cases in their projects.