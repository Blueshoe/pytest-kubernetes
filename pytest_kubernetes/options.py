from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ClusterOptions:
    api_version: str = field(default="1.25.3")
    # nodes: int = None
    kubeconfig_path: Path | None = None
    provider_config: Path | None = None  # Path to a Provider cluster config file
    cluster_timeout: int = field(default=240)
