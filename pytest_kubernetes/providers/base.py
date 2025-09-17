from abc import ABC, abstractmethod
import os
import shutil
import subprocess
from pathlib import Path
import tempfile
from time import sleep
from typing import Dict, List, Tuple, Union

import yaml

from pytest_kubernetes.kubectl import Kubectl
from pytest_kubernetes.options import ClusterOptions
from pytest_kubernetes.portforwarding import PortForwarding


class AClusterManager(ABC):
    """
    A manager to handle Kubernetes cluster providers.

    Attributes
    ----------
    cluster_name : str
        the name of this cluster
    kubeconfig : Path
        a Path instance to the kubeconfig file for this cluster (after it was created)
    context : str
        the name of the context (usually None)

    Methods
    -------
    kubectl():
        Execute kubectl command against this cluster
    apply():
        Apply resources to this cluster, either from YAML file, or Python dict
    load_image():
        Load a container image into this cluster
    logs():
        Get the logs of a pod
    port_forwarding():
        Port forward a target
    wait():
        Wait for a target to be ready
    version():
        Get the Kubernetes version of this cluster
    create():
        Create this cluster
    delete():
        Delete this cluster
    reset():
        Delete this cluster (if it exists) and create it again
    """

    _binary_name = ""
    _cluster_options: ClusterOptions = ClusterOptions()
    context = None

    def __init__(
        self,
        cluster_name: str | None = None,
        provider_config: str | None = None,
        kubeconfig: str | None = None,
    ) -> None:
        self._set_cluster_name(cluster_name, provider_config)
        self._ensure_executable()
        if kubeconfig:
            self._cluster_options.kubeconfig_path = kubeconfig

    def _set_cluster_name(self, cluster_name, provider_config) -> str:
        config_yaml = None
        if provider_config:
            self._cluster_options.provider_config = Path(provider_config)
            config_yaml = yaml.safe_load(
                self._cluster_options.provider_config.read_text()
            )

        if not self.cluster_name:
            default = f"pytest-{cluster_name}" if cluster_name else "pytest"
            if config_yaml:
                self._cluster_options.cluster_name = config_yaml.get("name", default)
            else:
                self._cluster_options.cluster_name = default
        return self.cluster_name

    @classmethod
    @abstractmethod
    def get_binary_name(cls) -> str:
        raise NotImplementedError

    @property
    def _exec_path(self) -> Path:
        return Path(str(shutil.which(self.get_binary_name())))

    def _ensure_executable(self) -> None:
        if not self._exec_path:
            raise RuntimeError("Executable is not set")

        if not self._exec_path.exists():
            raise RuntimeError("Executable not found")

    def _get_exec_env(self) -> Dict:
        return os.environ  # type: ignore

    def _exec(
        self,
        arguments: List[str],
        additional_env: Dict[str, str] = {},
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess:
        _timout = timeout or self._cluster_options.cluster_timeout
        proc = subprocess.run(
            f"{self._exec_path} {' '.join(arguments)}",
            env=self._get_exec_env().update(additional_env),
            shell=True,
            capture_output=True,
            check=True,
            timeout=_timout,
        )
        return proc

    @abstractmethod
    def _on_create(self, cluster_options: ClusterOptions, **kwargs) -> None:
        raise NotImplementedError

    @abstractmethod
    def _on_delete(self) -> None:
        raise NotImplementedError

    @property
    def kubeconfig(self) -> Path | None:
        return (
            Path(self._cluster_options.kubeconfig_path)
            if self._cluster_options.kubeconfig_path
            else None
        )

    @property
    def cluster_name(self) -> str:
        return self._cluster_options.cluster_name

    #
    # Interface
    #

    def kubectl(
        self, args: List[str], as_dict: bool = True, timeout: int = 60
    ) -> dict | str:
        """Execute kubectl command against this cluster"""
        return Kubectl(self.kubeconfig, self.context)(args, as_dict, timeout)

    def apply(self, input: Union[Path, Dict]) -> None:
        """Apply resources to this cluster, either from YAML file, or Python dict"""
        if type(input) in [Path, str] or isinstance(input, Path):
            self.kubectl(["apply", "-f", str(input)], as_dict=False)
        elif type(input) is dict:
            _yaml = yaml.dump(input)
            Kubectl(
                self.kubeconfig,
                self.context,
                command_prefix=[
                    "echo",
                    f"'{_yaml}'",
                    "|",
                ],
            )(["apply", "-f", "-"], as_dict=False)
        else:
            raise RuntimeError(f"Input must be of type Path or dict, was {type(input)}")

    def wait(
        self, name: str, waitfor: str, timeout: int = 90, namespace: str = "default"
    ) -> None:
        """Wait for a target and a contition"""
        self.kubectl(
            [
                "wait",
                name,
                f"--for={waitfor}",
                f"--timeout={timeout}s",
                f"--namespace={namespace}",
            ],
            as_dict=False,
            timeout=timeout,
        )

    def port_forwarding(
        self,
        target: str,
        source_port: int,
        target_port: int,
        namespace: str = "default",
        timeout: int = 90,
    ) -> PortForwarding:
        """Forward a local port to a pod"""
        return PortForwarding(
            target,
            (source_port, target_port),
            namespace,
            self.kubeconfig,
            self.context,
            timeout,
        )

    @abstractmethod
    def load_image(self, image: str) -> None:
        """Load a container image into this cluster"""
        raise NotImplementedError

    def logs(
        self, pod: str, container: str | None = None, namespace: str | None = None
    ) -> str:
        """Get the logs of a pod"""
        args = ["logs", pod]

        if namespace:
            args.extend(["-n", namespace])
        if container:
            args.extend(["-c", container])

        return self.kubectl(args, as_dict=False)  # type: ignore

    def version(self) -> Tuple[int, int]:
        """Get the Kubernetes version of this cluster"""
        data = self.kubectl(["version"])
        return int(data["serverVersion"]["major"]), int(data["serverVersion"]["minor"])  # type: ignore

    def create(
        self,
        cluster_options: ClusterOptions | None = None,
        timeout: int = 20,
        **kwargs,
    ) -> None:
        """Create this cluster"""
        self._cluster_options = cluster_options or self._cluster_options
        if not self._cluster_options.kubeconfig_path:
            tmp_kubeconfig = tempfile.NamedTemporaryFile(delete=False)
            tmp_kubeconfig.close()
            self._cluster_options.kubeconfig_path = Path(tmp_kubeconfig.name)
        # since we allow passing provider_configs in this method, we have to adapte the cluster name here
        if self._cluster_options.provider_config:
            self._set_cluster_name(
                self.cluster_name, self._cluster_options.provider_config
            )
        if not self.ready(timeout=2):
            self._on_create(self._cluster_options, **kwargs)
        # check if this cluster is ready: readyz check passed and default service account is available
        if not self.ready(timeout):
            raise RuntimeError(f"Cluster '{self.cluster_name}' is not ready.")

    def ready(self, timeout: int = 20) -> bool:
        """Check if this cluster is ready"""
        _i = 0
        ready = "Nope"
        sa_available = "Nope"
        while _i < timeout:
            sleep(1)
            try:
                ready = str(
                    self.kubectl(["get", "--raw='/readyz?verbose'"], as_dict=False)
                )
                sa_available = str(
                    self.kubectl(
                        ["get", "sa", "default", "-n", "default"], as_dict=False
                    )
                )
            except RuntimeError:
                _i += 1
                continue
            if "readyz check passed" in ready and "not found" not in sa_available:
                break
            else:
                _i += 1
        else:
            return False
        return True

    def delete(self) -> None:
        """Delete this cluster"""
        self._on_delete()
        if self.kubeconfig:
            self.kubeconfig.unlink(missing_ok=True)
            self._cluster_options.kubeconfig_path = None
        sleep(1)

    def reset(self) -> None:
        """Reset this cluster (delete if exists and recreates)"""
        self.delete()
        self.create()
