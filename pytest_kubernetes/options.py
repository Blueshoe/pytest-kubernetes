from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ClusterOptions:
    cluster_name: str = ""
    api_version: str = field(default="1.25.3")
    # nodes: int = None
    kubeconfig_path: Path | None = None
    provider_config: Path | None = None  # Path to a Provider cluster config file
    cluster_timeout: int = field(default=240)

    # https://stackoverflow.com/questions/77673392/merging-two-dataclasses
    def __or__(self, other):
        return self.__class__(**asdict(self) | asdict(other))
