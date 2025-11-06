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


def load_prompts() -> dict[str, str]:
    data = load_config()
    return data.get("prompts", {})


def load_prompt_defaults() -> dict[str, str]:
    data = load_config()
    return data.get("prompt_defaults", {})


def load_prompt_components() -> dict[str, Any]:
    data = load_config()
    return data.get("prompt_components", {})


def load_scheduling() -> dict[str, Any]:
    data = load_config()
    return data.get("scheduling", {})


def load_tracking() -> dict[str, Any]:
    data = load_config()
    return data.get("tracking", {})


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
