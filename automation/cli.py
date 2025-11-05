import asyncio
import subprocess
import sys

from automation import COMFY_ROOT
from automation.core import batch_generate, generate_templates, generate_video
from automation.models import sync_wan_assets
from automation.script import generate_basic_render
from automation.workflows import WAN_TEMPLATES, load_prompts, load_prompt_defaults

PROMPT_MAP = load_prompts()
PROMPT_DEFAULTS = load_prompt_defaults()


def main() -> None:
    argv = sys.argv[1:]
    if argv and argv[0] in {"start-server", "automate", "render", "download-models", "templates"}:
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
        if args:
            prompt_keys = args[0].split("||")
            tail = list(args[1:])
        else:
            prompt_keys = [PROMPT_DEFAULTS["automate"]]
            tail = []
        prompts = []
        for key in prompt_keys:
            if key in PROMPT_MAP:
                prompts.append(PROMPT_MAP[key])
                continue
            if key in WAN_TEMPLATES:
                prompts.append("")
                if not tail:
                    tail = [key]
                continue
            prompts.append(PROMPT_MAP[key])
        mode = tail[0] if tail else "wan"
        if len(prompts) > 1:
            asyncio.run(batch_generate(prompts, mode, **kwargs))
            return
        asyncio.run(generate_video(prompts[0], mode, **kwargs))
        return
    if command == "templates":
        names = args if args else None
        asyncio.run(generate_templates(names))
        return
    if command == "download-models":
        sync_wan_assets()
        return
    if args:
        prompt_key = args[0]
        tail = args[1:]
    else:
        prompt_key = PROMPT_DEFAULTS["script"]
        tail = []
    prompt = PROMPT_MAP[prompt_key]
    output = tail[0] if tail else "output.mp4"
    generate_basic_render(prompt, output)
