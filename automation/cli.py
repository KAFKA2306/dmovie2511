import asyncio
import subprocess
import sys

from automation import COMFY_ROOT
from automation.core import batch_generate, generate_video
from automation.models import sync_wan_assets
from automation.script import generate_basic_render


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] in {"start-server", "automate", "render", "download-models"}:
        command = argv[0]
        args = argv[1:]
    else:
        command = "automate"
        args = argv
    if command == "start-server":
        subprocess.run([
            "uv",
            "run",
            "python",
            str(COMFY_ROOT / "main.py"),
            "--listen",
            "127.0.0.1",
            "--port",
            "8188",
        ])
        return
    if command == "automate":
        preset = None
        if "--preset" in args:
            preset_idx = args.index("--preset")
            preset = args[preset_idx + 1]
            args = args[:preset_idx] + args[preset_idx + 2:]
        kwargs = {"preset": preset} if preset else {}
        if len(args) > 1:
            prompts = args[0].split("||")
            mode = args[1]
            asyncio.run(batch_generate(prompts, mode, **kwargs))
            return
        prompt = args[0] if args else "cinematic shot of a sunset over mountains"
        mode = args[1] if len(args) > 1 else "wan"
        asyncio.run(generate_video(prompt, mode, **kwargs))
        return
    if command == "download-models":
        sync_wan_assets()
        return
    prompt = args[0] if args else "a beautiful landscape"
    output = args[1] if len(args) > 1 else "output.mp4"
    generate_basic_render(prompt, output)
