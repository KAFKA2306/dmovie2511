import sys
import json
import asyncio
import time
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
            print(f"ComfyUI response: {resp.json()}")
            return resp.json()["prompt_id"]
    async def wait_for_completion(self, prompt_id: str):
        async with websockets.connect(f"{self.ws_url}?clientId={self.client_id}") as ws:
            while True:
                msg = json.loads(await ws.recv())
                if msg["type"] == "executing" and msg["data"]["node"] is None:
                    break
    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.http_url}/history/{prompt_id}")
            return resp.json()[prompt_id]
async def generate_video(prompt: str, mode: str = "wan", **kwargs):
    client = ComfyUIClient()
    workflow = {}
    if mode == "wan":
        seed = kwargs.get("seed", 42)
        steps = kwargs.get("steps", 24)
        cfg = kwargs.get("cfg", 7.5)
        width = kwargs.get("width", 512)
        height = kwargs.get("height", 320)
        frames = kwargs.get("frames", 16)
        frame_rate = kwargs.get("frame_rate", 12)
        
        text_encoder_name = kwargs.get("text_encoder_name", "umt5-xxl-enc-bf16.safetensors")
        model_name = kwargs.get("model_name", "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors")
        vae_name = kwargs.get("vae_name", "Wan2_1_VAE_bf16.safetensors")
        filename_prefix = kwargs.get("filename_prefix", "wan_output")

        workflow = {
            "1": {
                "class_type": "WanVideoTextEncodeCached",
                "inputs": {
                    "model_name": text_encoder_name,
                    "precision": "bf16",
                    "positive_prompt": prompt,
                    "negative_prompt": kwargs.get("negative_prompt", ""),
                    "quantization": "disabled",
                    "use_disk_cache": True,
                    "device": "gpu"
                }
            },
            "2": {
                "class_type": "WanVideoModelLoader",
                "inputs": {
                    "model": model_name,
                    "base_precision": "bf16",
                    "quantization": "fp8_e4m3fn_scaled",
                    "load_device": "offload_device"
                }
            },
            "3": {
                "class_type": "WanVideoVAELoader",
                "inputs": {
                    "model_name": vae_name,
                    "precision": "bf16"
                }
            },
            "4": {
                "class_type": "WanVideoEmptyEmbeds",
                "inputs": {
                    "width": width,
                    "height": height,
                    "num_frames": frames
                }
            },
            "5": {
                "class_type": "WanVideoSampler",
                "inputs": {
                    "model": ["2", 0],
                    "image_embeds": ["4", 0],
                    "text_embeds": ["1", 0],
                    "steps": steps,
                    "cfg": cfg,
                    "shift": 5.0,
                    "seed": seed,
                    "force_offload": True,
                    "scheduler": "unipc",
                    "riflex_freq_index": 0
                }
            },
            "6": {
                "class_type": "WanVideoDecode",
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["3", 0],
                    "enable_vae_tiling": False,
                    "tile_x": 272,
                    "tile_y": 272,
                    "tile_stride_x": 144,
                    "tile_stride_y": 128
                }
            },
            "7": {
                "class_type": "VHS_VideoCombine",
                "inputs": {
                    "images": ["6", 0],
                    "frame_rate": frame_rate,
                    "loop_count": 0,
                    "filename_prefix": filename_prefix,
                    "format": "video/h264-mp4",
                    "pingpong": False,
                    "save_output": True
                }
            }
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

