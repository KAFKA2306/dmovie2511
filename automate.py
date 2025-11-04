import sys
import json
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "ComfyUI"))

import httpx
import websockets
from typing import Dict, Any


class ComfyUIClient:
    def __init__(self, server_url: str = "127.0.0.1:8188"):
        self.server_url = server_url
        self.http_url = f"http://{server_url}"
        self.ws_url = f"ws://{server_url}/ws"
        self.client_id = "automation_client"

    async def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.http_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id},
            )
            return response.json()["prompt_id"]

    async def wait_for_completion(self, prompt_id: str):
        async with websockets.connect(f"{self.ws_url}?clientId={self.client_id}") as ws:
            while True:
                msg = json.loads(await ws.recv())
                if msg["type"] == "executing" and msg["data"]["prompt_id"] == prompt_id:
                    if msg["data"]["node"] is None:
                        break

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.http_url}/history/{prompt_id}")
            return response.json()[prompt_id]


def create_wan_video_workflow(prompt: str, seed: int = 42) -> Dict[str, Any]:
    return {
        "1": {
            "inputs": {"prompt": prompt, "seed": seed, "steps": 50, "cfg": 7.5},
            "class_type": "WanVideoTextEncode",
        },
        "2": {
            "inputs": {
                "conditioning": ["1", 0],
                "frames": 16,
                "width": 512,
                "height": 512,
            },
            "class_type": "WanVideoSample",
        },
        "3": {
            "inputs": {"samples": ["2", 0], "filename_prefix": "wan_output"},
            "class_type": "SaveVideo",
        },
    }


def create_kling_video_workflow(prompt: str, api_key: str) -> Dict[str, Any]:
    return {
        "1": {
            "inputs": {
                "api_key": api_key,
            },
            "class_type": "KlingAIClient",
        },
        "2": {
            "inputs": {
                "client": ["1", 0],
                "prompt": prompt,
                "duration": 5,
                "aspect_ratio": "16:9",
            },
            "class_type": "KlingTextToVideo",
        },
        "3": {
            "inputs": {"video": ["2", 0], "filename_prefix": "kling_output"},
            "class_type": "SaveVideo",
        },
    }


async def generate_video(prompt: str, mode: str = "wan", **kwargs):
    client = ComfyUIClient()

    if mode == "wan":
        workflow = create_wan_video_workflow(prompt, kwargs.get("seed", 42))
    elif mode == "kling":
        api_key = kwargs.get("api_key")
        if not api_key:
            raise ValueError("api_key required for kling mode")
        workflow = create_kling_video_workflow(prompt, api_key)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    prompt_id = await client.queue_prompt(workflow)
    await client.wait_for_completion(prompt_id)
    history = await client.get_history(prompt_id)

    return history


async def batch_generate(prompts: list[str], mode: str = "wan", **kwargs):
    tasks = [generate_video(p, mode, **kwargs) for p in prompts]
    return await asyncio.gather(*tasks)


if __name__ == "__main__":
    prompt = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "cinematic shot of a sunset over mountains"
    )
    mode = sys.argv[2] if len(sys.argv) > 2 else "wan"

    asyncio.run(generate_video(prompt, mode))
