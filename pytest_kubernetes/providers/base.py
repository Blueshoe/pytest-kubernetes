from abc import ABC, abstractmethod
import os
import shutil
import subprocess
from pathlib import Path
import tempfile
from time import sleep
from typing import Dict, List, Optional, Tuple, Union

import yaml

from pytest_kubernetes.kubectl import Kubectl
from pytest_kubernetes.options import ClusterOptions


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
    cluster_name = ""
    context = None

    def __init__(self, cluster_name: str) -> None:
        self.cluster_name = f"pytest-{cluster_name}"
        self._ensure_executable()

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
        timeout: Optional[int] = None,
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
    def kubeconfig(self) -> Optional[Path]:
        return (
            Path(self._cluster_options.kubeconfig_path)
            if self._cluster_options.kubeconfig_path
            else None
        )

    #
    # Interface
    #

    def kubectl(self, args: List[str], as_dict: bool = True) -> Union[Dict, str]:
        """Execute kubectl command against this cluster"""
        return Kubectl(self.kubeconfig, self.context)(args, as_dict)

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

    @abstractmethod
    def load_image(self, image: str) -> None:
        """Load a container image into this cluster"""
        raise NotImplementedError

    def logs(self, pod: str, container: Optional[str] = None) -> str:
        """Get the logs of a pod"""
        return self.kubectl(  # type: ignore
            ["logs", pod] + (["-c", container] if container else []),
            as_dict=False,
        )

    def version(self) -> Tuple[int, int]:
        """Get the Kubernetes version of this cluster"""
        data = self.kubectl(["version"])
        return int(data["serverVersion"]["major"]), int(data["serverVersion"]["minor"])  # type: ignore

    def create(self, cluster_options: Optional[ClusterOptions] = None, **kwargs) -> None:
        """Create this cluster"""
        self._cluster_options = cluster_options or self._cluster_options
        if not self._cluster_options.kubeconfig_path:
            tmp_kubeconfig = tempfile.NamedTemporaryFile(delete=False)
            tmp_kubeconfig.close()
            self._cluster_options.kubeconfig_path = Path(tmp_kubeconfig.name)
        self._on_create(self._cluster_options, **kwargs)
        _i = 0
        # check if this cluster is ready: readyz check passed and default service account is available
        while _i < 20:
            sleep(1)
            try:
                ready = self.kubectl(["get", "--raw='/readyz?verbose'"], as_dict=False)
                sa_available = self.kubectl(["get", "sa", "default"], as_dict=False)
            except RuntimeError:
                _i += 1
                continue
            if "readyz check passed" in ready and "not found" not in sa_available:
                break
            else:
                _i += 1
        else:
            raise RuntimeError(f"Cluster '{self.cluster_name}' is not ready")

    def delete(self) -> None:
        """Delete this cluster"""
        self._on_delete()
        if self.kubeconfig:
            self.kubeconfig.unlink(missing_ok=True)
        sleep(1)

    def reset(self) -> None:
        """Reset this cluster (delete if exists and recreates)"""
        self.delete()
        self.create()
