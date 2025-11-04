import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any
import httpx
import websockets
sys.path.insert(0, str(Path(__file__).parent / "ComfyUI"))
class ComfyUIClient:
    def __init__(self, server_url: str = "127.0.0.1:8188"):
        self.server_url = server_url
        self.http_url = f"http://{server_url}"
        self.ws_url = f"ws://{server_url}/ws"
        self.client_id = "automation_client"
    async def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.http_url}/prompt", json={"prompt": workflow, "client_id": self.client_id})
            return resp.json()["prompt_id"]
    async def wait_for_completion(self, prompt_id: str):
        async with websockets.connect(f"{self.ws_url}?clientId={self.client_id}") as ws:
            while True:
                msg = json.loads(await ws.recv())
                if msg["type"] == "executing" and msg["data"]["prompt_id"] == prompt_id and msg["data"]["node"] is None:
                    break
    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.http_url}/history/{prompt_id}")
            return resp.json()[prompt_id]
async def generate_video(prompt: str, mode: str = "wan", **kwargs):
    client = ComfyUIClient()
    workflow = {}
    if mode == "wan":
        workflow = {
            "1": {"inputs": {"prompt": prompt, "seed": kwargs.get("seed", 42), "steps": 50, "cfg": 7.5}, "class_type": "WanVideoTextEncode"},
            "2": {"inputs": {"conditioning": ["1", 0], "frames": 16, "width": 512, "height": 512}, "class_type": "WanVideoSample"},
            "3": {"inputs": {"samples": ["2", 0], "filename_prefix": "wan_output"}, "class_type": "SaveVideo"},
        }
    elif mode == "kling":
        workflow = {
            "1": {"inputs": {"api_key": kwargs.get("api_key")}, "class_type": "KlingAIClient"},
            "2": {"inputs": {"client": ["1", 0], "prompt": prompt, "duration": 5, "aspect_ratio": "16:9"}, "class_type": "KlingTextToVideo"},
            "3": {"inputs": {"video": ["2", 0], "filename_prefix": "kling_output"}, "class_type": "SaveVideo"},
        }
    prompt_id = await client.queue_prompt(workflow)
    await client.wait_for_completion(prompt_id)
    return await client.get_history(prompt_id)
async def batch_generate(prompts: list[str], mode: str = "wan", **kwargs):
    return await asyncio.gather(*(generate_video(p, mode, **kwargs) for p in prompts))
if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "cinematic shot of a sunset over mountains"
    mode = sys.argv[2] if len(sys.argv) > 2 else "wan"
    asyncio.run(generate_video(prompt, mode))