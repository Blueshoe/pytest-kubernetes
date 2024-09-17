import io
from pathlib import Path
import subprocess
import tempfile
from time import sleep
from typing import List, Tuple

from pytest_kubernetes.kubectl import Kubectl


class PortForwarding(Kubectl):
    """Port forwarding for a target. A target can be a pod, deployment, statefulset or a service.

    This class is responsible for setting up port forwarding for the target. It
    will start a process that will forward the specified ports to the pod.
    The process will be stopped when the object is destroyed.
    """

    def __init__(
        self,
        target: str,
        ports: Tuple[int, int],
        namespace: str = "default",
        kubeconfig: Path | None = None,
        context: str | None = None,
        timeout: int = 90,
    ):
        self._target = target
        self._ports = ports
        self._process = None
        self._kubeconfig = kubeconfig
        self._context = context
        self._namespace = namespace
        self._timeout = timeout

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

    def start(self):
        """Start the port forwarding process."""
        if self._process:
            raise RuntimeError("Port forwarding already started")
        self._log = tempfile.TemporaryFile()
        self._forward()
        _t = self._timeout
        while _t > 0:
            self._log.seek(0)
            if "Forwarding from" in self._log.read().decode("utf-8"):
                break
            self._log.seek(0, io.SEEK_END)
            sleep(1)
            _t -= 1
        else:
            self._log.seek(0)
            logs = self._log.read().decode("utf-8")
            self.stop()
            raise RuntimeError(f"Port forwarding failed with error: {logs}")

    def stop(self):
        """Stop the port forwarding process."""
        import socket

        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None
            self._log.close()
            _t = self._timeout
            # make sure this port forwarding is stopped
            while _t > 0:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                socket.setdefaulttimeout(2.0)
                result = s.connect_ex(("127.0.0.1", int(self._ports[0])))
                s.close()
                if result == 0:
                    _t -= 1
                    sleep(1)
                    continue
                else:
                    break
            else:
                raise RuntimeError("Port forwarding failed to stop")

    def _exec(self, arguments: List[str]) -> subprocess.Popen:  # type: ignore
        proc = subprocess.Popen(
            [str(self._exec_path)] + self._get_kubeconfig_args() + arguments,
            stdout=self._log,
            stderr=self._log,
        )
        return proc

    def _forward(self):
        """Forward the ports to the target."""
        # Create the port forwarding command.
        self._process = self._exec(
            [
                "port-forward",
                self._target,
                "--namespace",
                self._namespace,
                f"{self._ports[0]}:{self._ports[1]}",
                f"--pod-running-timeout={self._timeout}s",
            ]
        )
