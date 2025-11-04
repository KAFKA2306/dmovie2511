import subprocess
from pathlib import Path
comfyui_path = Path(__file__).parent / "ComfyUI"
subprocess.run(["uv", "run", "python", str(comfyui_path / "main.py"), "--listen", "127.0.0.1", "--port", "8188"])