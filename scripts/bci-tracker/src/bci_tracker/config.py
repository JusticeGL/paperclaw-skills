from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


DEFAULT_CONFIG_PATH = Path("config.yaml")


class ConfigError(ValueError):
    pass


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ConfigError("config root must be a mapping")
    validate_config(data)
    data["_config_path"] = str(config_path)
    return data


def validate_config(cfg: Dict[str, Any]) -> None:
    required = ["timezone", "window_days", "sources", "keywords", "selection", "output"]
    missing = [key for key in required if key not in cfg]
    if missing:
        raise ConfigError(f"config missing required keys: {missing}")
    if int(cfg["window_days"]) < 0:
        raise ConfigError("window_days cannot be negative")

    selection = cfg["selection"]
    if selection["total_min"] > selection["total_max"]:
        raise ConfigError("selection.total_min cannot exceed selection.total_max")
    output = cfg["output"]
    for key in ["dir", "candidates_filename", "final_filename"]:
        if not output.get(key):
            raise ConfigError(f"output.{key} is required")


def output_dir(cfg: Dict[str, Any]) -> Path:
    path = Path(cfg["output"]["dir"]).expanduser()
    if not path.is_absolute():
        base = Path(cfg.get("_config_path", ".")).resolve().parent
        path = base / path
    return path
