from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ClusterOptions:
    cluster_name: str | None = None
    api_version: str = field(default="1.25.3")
    # nodes: int = None
    kubeconfig_path: Path | None = None
    provider_config: Path | None = None  # Path to a Provider cluster config file
    cluster_timeout: int = field(default=240)

    # https://stackoverflow.com/questions/77673392/merging-two-dataclasses
    def __or__(self, other):
        this = {k: v for k, v in asdict(self).items() if v is not None}
        other = {k: v for k, v in asdict(other).items() if v is not None}
        return self.__class__(**this | other)
