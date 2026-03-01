"""Loads pipeline/config.yaml with optional env var overrides."""
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

_HERE = Path(__file__).parent
_DEFAULT = _HERE / "config.yaml"


def _load() -> dict:
    with open(_DEFAULT) as f:
        cfg = yaml.safe_load(f)
    # Env var overrides (dot-separated key path, e.g. RADAR_WEIGHTS__GROWTH=0.40)
    for key, val in os.environ.items():
        if not key.startswith("RADAR_"):
            continue
        parts = key[len("RADAR_"):].lower().split("__")
        node = cfg
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        try:
            node[parts[-1]] = yaml.safe_load(val)
        except Exception:
            node[parts[-1]] = val
    return cfg


_cfg: dict[str, Any] = _load()


def get(path: str, default: Any = None) -> Any:
    """Dot-separated path lookup, e.g. get('weights.growth')."""
    node = _cfg
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def all_config() -> dict:
    return _cfg
