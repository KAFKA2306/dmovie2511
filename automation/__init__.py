from pathlib import Path
import sys

COMFY_ROOT = Path(__file__).resolve().parent.parent / "ComfyUI"


def ensure_comfy_path() -> None:
    path = str(COMFY_ROOT)
    if path not in sys.path:
        sys.path.insert(0, path)
