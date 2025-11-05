from pathlib import Path
from typing import Any

import yaml


def load_config() -> dict[str, Any]:
    path = Path(__file__).resolve().parent.parent / "config" / "workflows.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_presets() -> dict[str, dict[str, Any]]:
    data = load_config()
    return data.get("presets", {})


def load_defaults() -> dict[str, Any]:
    data = load_config()
    return data.get("defaults", {})


def load_templates() -> dict[str, dict[str, Any]]:
    data = load_config()
    defaults = data.get("defaults", {})
    templates = data.get("templates", {})
    result: dict[str, dict[str, Any]] = {}
    for name, values in templates.items():
        combined = dict(defaults)
        combined.update(values)
        result[name] = combined
    return result


WAN_TEMPLATES = load_templates()
