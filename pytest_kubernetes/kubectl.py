import json
from typing import Dict, Union
import os
from pathlib import Path
import shutil
import subprocess
from typing import List


class Kubectl:
    """A wrapper for the kubectl command."""

    _kubeconfig = None
    _context = None

    def __init__(
        self,
        kubeconfig: Path | None = None,
        context: str | None = None,
        command_prefix: List[str] | None = None,
    ) -> None:
        if kubeconfig is None:
            raise RuntimeError("The kubeconfig is not set. Did you create the cluster?")
        self._kubeconfig = kubeconfig
        self._context = context
        self._prefix = command_prefix

    @property
    def _exec_path(self) -> Path:
        return Path(str(shutil.which("kubectl")).strip())

    def _ensure_executable(self) -> None:
        if not self._exec_path:
            raise RuntimeError("Executable is not set")

        if not self._exec_path.exists():
            raise RuntimeError("Executable not found")

    def _get_exec_env(self) -> Dict:
        return os.environ  # type: ignore

    def _get_command_prefix(self) -> List[str]:
        return self._prefix or []

    def _get_kubeconfig_args(self) -> List[str]:
        args = ["--kubeconfig", str(self._kubeconfig)]
        if self._context:
            args += ["--context", str(self._context)]
        return args

    def _exec(
        self, arguments: List[str], timeout: int = 60
    ) -> subprocess.CompletedProcess:
        try:
            proc = subprocess.run(
                " ".join(
                    self._get_command_prefix()
                    + [str(self._exec_path)]
                    + self._get_kubeconfig_args()
                    + arguments
                ),
                shell=True,
                env=self._get_exec_env(),
                capture_output=True,
                check=True,
                timeout=timeout,
            )
            return proc
        except subprocess.CalledProcessError as e:
            raise RuntimeError(e.stderr.decode("utf-8")) from None

    def __call__(
        self, args: List[str], as_dict: bool = True, timeout: int = 60
    ) -> Union[Dict, str]:
        if as_dict:
            args += ["-o", "json"]
        try:
            proc = self._exec(args, timeout=timeout)
        except RuntimeError as e:
            if as_dict and "unknown shorthand flag" in str(e):
                raise RuntimeError(
                    "Cannot parse kubectl command into Dict. Please use kubectl([..], as_dict=False) to return a string"
                ) from None
            else:
                raise e
        output: str = proc.stdout.decode("utf-8")
        if as_dict:
            return json.loads(output)  # type: ignore
        return output
