from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ClusterOptions:
    api_version: str = field(default="1.25.3")
    # nodes: int = None
    kubeconfig_path: Optional[Path] = None
    cluster_timeout: int = field(default=120)
