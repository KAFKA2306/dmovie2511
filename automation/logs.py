import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from . import COMFY_ROOT
LOG_DIRECTORY = COMFY_ROOT / "logs"
def _timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"
def append_log(path: Path, payload: Dict[str, Any]) -> None:
    data = dict(payload)
    if not data.get("timestamp"):
        data["timestamp"] = _timestamp()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")
def append_named_log(name: str, payload: Dict[str, Any]) -> None:
    append_log(LOG_DIRECTORY / name, payload)
