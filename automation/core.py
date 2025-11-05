import asyncio
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import httpx
import websockets

from .workflows import WAN_TEMPLATES, load_defaults, load_presets

CAMERA_MOVES: Tuple[str, ...] = (
    "sinuous gimbal orbit weaving between foreground architecture",
    "low altitude drone chase with accelerating parallax arcs",
    "steadicam glide with organic drift and counterbalanced pivots",
    "multi-axis crane sweep threading vertical reveals through skyline layers",
)
LIGHTING_STYLES: Tuple[str, ...] = (
    "sunrise amber key balanced with cool bounce diffusers and shimmering rim lights",
    "diffused cloud cover enriched by lantern glow and volumetric shafts",
    "directional hard light softened with programmable LED wraps and reflective boards",
    "nocturnal neon ambience layered with practical sconces and motivated edge bloom",
)
COLOR_GRADES: Tuple[str, ...] = (
    "rich teal and amber duotone graded through an ACES pipeline",
    "twilight magenta and cobalt palette with lifted film grain",
    "earthy greens contrasted by tungsten highlights and cyan lift",
    "neutral cinematic log curve accented by saturated primaries and clean skin tones",
)
LENS_PROFILES: Tuple[str, ...] = (
    "anamorphic 35mm glass with elongated bokeh and restrained distortion",
    "vintage spherical primes delivering micro-contrast and minimal breathing",
    "modern full-frame zoom stabilized with inertial dampening",
    "macro hybrid optics capturing tactile textures with measured focus falloff",
)
CAPTURE_TECHNIQUES: Tuple[str, ...] = (
    "motion control rails synchronized to choreography cues",
    "dual-operator focus pulling with predictive overlays",
    "multi-axis dolly choreography blended with under-slung craning",
    "volumetric cloud capture interleaved with temporal supersampling",
)
TEXTURE_DETAILS: Tuple[str, ...] = (
    "floating dust motes, rain streak refractions, and reflective puddles",
    "wind-driven fabric, cascading hair strands, and polished metal gleams",
    "bokeh-laced speculars, mist-laden air currents, and luminous signage",
    "crystalline particles, cinematic lens flares, and shimmering water vapor",
)
POST_TREATMENTS: Tuple[str, ...] = (
    "film emulation LUTs, halation bloom, and Dolby Vision trim passes",
    "spectral denoisers, layered grain, and HDR10 mastering sweeps",
    "AI-assisted interpolation, chroma refinement, and selective dehaze",
    "ACEScg balancing, channel isolation, and per-channel sharpening",
)

LOG_FILE = Path(__file__).resolve().parent.parent / "ComfyUI" / "logs" / "automation_events.jsonl"


def _prompt_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _write_log(payload: Dict[str, Any]) -> None:
    data = dict(payload)
    data["timestamp"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def _descriptor_index(prompt: str) -> int:
    return sum(ord(ch) for ch in prompt)


def _pick_descriptor(prompt: str, items: Tuple[str, ...], offset: int) -> str:
    idx = _descriptor_index(prompt)
    return items[(idx + offset) % len(items)]


def enrich_prompt(base_prompt: str) -> str:
    text = base_prompt.strip() or "cinematic motion study with layered environments"
    camera = _pick_descriptor(text, CAMERA_MOVES, 0)
    lighting = _pick_descriptor(text, LIGHTING_STYLES, 1)
    grade = _pick_descriptor(text, COLOR_GRADES, 2)
    lens = _pick_descriptor(text, LENS_PROFILES, 3)
    technique = _pick_descriptor(text, CAPTURE_TECHNIQUES, 4)
    texture = _pick_descriptor(text, TEXTURE_DETAILS, 5)
    post = _pick_descriptor(text, POST_TREATMENTS, 6)
    segments = [
        f"Cinematic portrayal of {text} with orchestrated focus cues and layered atmospheric depth for grand scale.",
        f"Camera executes a {camera} path with responsive stabilization to sustain fluid parallax and articulate every spatial plane.",
        f"Lighting relies on {lighting} while volumetric haze shapes silhouettes and highlights moving subjects.",
        f"Color palette leans on {grade} to preserve nuanced gradients during rapid motion.",
        f"Lens emulation mirrors {lens} alongside {technique} to emphasize dimensionality and subject separation.",
        f"Surface detail features {texture} that animate through the frame without smearing.",
        f"Post-production integrates {post} and cinematic motion blur tuned for twenty-four frame playback.",
    ]
    prompt = " ".join(segments)
    filler = "Advanced audio-reactive motion curves maintain rhythm and micro-timing edits reinforce narrative continuity."
    words = prompt.split()
    while len(words) < 80:
        prompt = f"{prompt} {filler}"
        words = prompt.split()
    if len(words) > 120:
        prompt = " ".join(words[:120])
    return prompt

class ComfyUIClient:
    def __init__(self, server_url: str = "127.0.0.1:8188") -> None:
        self.server_url = server_url
        self.http_url = f"http://{server_url}"
        self.ws_url = f"ws://{server_url}/ws"
        self.client_id = "automation_client"

    async def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.http_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id},
            )
            data = resp.json()
            print(f"ComfyUI response: {data}")
            return data["prompt_id"]

    async def wait_for_completion(self, prompt_id: str) -> None:
        async with websockets.connect(f"{self.ws_url}?clientId={self.client_id}") as ws:
            while True:
                msg = json.loads(await ws.recv())
                if msg["type"] == "executing" and msg["data"]["node"] is None:
                    break

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.http_url}/history/{prompt_id}")
            data = resp.json()
            return data[prompt_id]


def build_wan_workflow(prompt: str, **kwargs: Any) -> Dict[str, Any]:
    preset_name = kwargs.get("preset")
    if preset_name:
        presets = load_presets()
        preset = presets.get(preset_name, {})
        defaults = load_defaults()
        merged = dict(defaults)
        merged.update(preset)
        merged.update(kwargs)
        kwargs = merged
    seed = kwargs.get("seed", 42)
    quality_mode = kwargs.get("quality_mode", "standard")
    steps = kwargs.get("steps", 50)
    if quality_mode == "high":
        steps = kwargs.get("high_quality_steps", steps)
    cfg = kwargs.get("cfg", 7.0)
    dual_pass_cfg = kwargs.get("dual_pass_cfg", 3.5)
    width = kwargs.get("width", 1280)
    height = kwargs.get("height", 720)
    frames = kwargs.get("frames", 81)
    frame_rate = kwargs.get("frame_rate", 24)
    text_encoder_name = kwargs.get("text_encoder_name", "umt5-xxl-enc-bf16.safetensors")
    model_name = kwargs.get("model_name", "wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors")
    vae_name = kwargs.get("vae_name", "Wan2_1_VAE_bf16.safetensors")
    filename_prefix = kwargs.get("filename_prefix", "wan_output")
    negative_prompt = kwargs.get("negative_prompt", "")
    schedulers = kwargs.get("schedulers", {})
    stage_one_scheduler = schedulers.get("stage_one", "euler")
    stage_two_scheduler = schedulers.get("stage_two", "beta")
    dual_stage = kwargs.get("dual_stage", {})
    dual_stage_enabled = dual_stage.get("enabled", False)
    stage_one_steps = dual_stage.get("stage_one_steps", steps)
    stage_two_steps = dual_stage.get("stage_two_steps", steps)
    dual_stage_denoise = dual_stage.get("denoise", 0.45)
    workflow: Dict[str, Any] = {
        "1": {
            "class_type": "WanVideoTextEncodeCached",
            "inputs": {
                "model_name": text_encoder_name,
                "precision": "bf16",
                "positive_prompt": prompt,
                "negative_prompt": negative_prompt,
                "quantization": "disabled",
                "use_disk_cache": True,
                "device": "gpu",
            },
        },
        "2": {
            "class_type": "WanVideoModelLoader",
            "inputs": {
                "model": model_name,
                "base_precision": "bf16",
                "quantization": "fp8_e4m3fn_scaled",
                "load_device": "offload_device",
            },
        },
        "3": {
            "class_type": "WanVideoVAELoader",
            "inputs": {
                "model_name": vae_name,
                "precision": "bf16",
            },
        },
        "4": {
            "class_type": "WanVideoEmptyEmbeds",
            "inputs": {
                "width": width,
                "height": height,
                "num_frames": frames,
            },
        },
    }
    if dual_stage_enabled:
        workflow["5"] = {
            "class_type": "WanVideoSampler",
            "inputs": {
                "model": ["2", 0],
                "image_embeds": ["4", 0],
                "text_embeds": ["1", 0],
                "steps": stage_one_steps,
                "cfg": cfg,
                "shift": 5.0,
                "seed": seed,
                "force_offload": True,
                "scheduler": stage_one_scheduler,
                "riflex_freq_index": 0,
            },
        }
        workflow["6"] = {
            "class_type": "WanVideoSampler",
            "inputs": {
                "model": ["2", 0],
                "image_embeds": ["4", 0],
                "text_embeds": ["1", 0],
                "samples": ["5", 0],
                "steps": stage_two_steps,
                "cfg": dual_pass_cfg,
                "shift": 5.0,
                "seed": seed,
                "force_offload": True,
                "scheduler": stage_two_scheduler,
                "riflex_freq_index": 0,
                "denoise_strength": dual_stage_denoise,
            },
        }
        sampler_output = ["6", 0]
        decode_key = "7"
        combine_key = "8"
    else:
        workflow["5"] = {
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
                "scheduler": stage_one_scheduler,
                "riflex_freq_index": 0,
            },
        }
        sampler_output = ["5", 0]
        decode_key = "6"
        combine_key = "7"
    workflow[decode_key] = {
        "class_type": "WanVideoDecode",
        "inputs": {
            "samples": sampler_output,
            "vae": ["3", 0],
            "enable_vae_tiling": False,
            "tile_x": 272,
            "tile_y": 272,
            "tile_stride_x": 144,
            "tile_stride_y": 128,
        },
    }
    workflow[combine_key] = {
        "class_type": "VHS_VideoCombine",
        "inputs": {
            "images": [decode_key, 0],
            "frame_rate": frame_rate,
            "loop_count": 0,
            "filename_prefix": filename_prefix,
            "format": "video/h264-mp4",
            "pingpong": False,
            "save_output": True,
        },
    }
    return workflow


async def generate_video(prompt: str, mode: str = "wan", **kwargs: Any) -> Dict[str, Any]:
    client = ComfyUIClient()
    preset = kwargs.get("preset")
    used_prompt = prompt
    workflow: Dict[str, Any]
    if mode == "wan":
        workflow = build_wan_workflow(enrich_prompt(used_prompt), **kwargs)
    else:
        template = WAN_TEMPLATES.get(mode)
        if template:
            data = template.copy()
            data.update(kwargs)
            template_prompt = data.pop("prompt", "")
            used_prompt = prompt or template_prompt
            workflow = build_wan_workflow(enrich_prompt(used_prompt), **data)
        else:
            workflow = {}
    digest = _prompt_digest(used_prompt)
    words = len(used_prompt.split())
    start_time = datetime.utcnow()
    _write_log({"event": "queue_start", "mode": mode, "preset": preset, "prompt_digest": digest, "words": words})
    prompt_id = await client.queue_prompt(workflow)
    _write_log({"event": "queued", "mode": mode, "preset": preset, "prompt_id": prompt_id, "prompt_digest": digest})
    await client.wait_for_completion(prompt_id)
    history = await client.get_history(prompt_id)
    elapsed = (datetime.utcnow() - start_time).total_seconds()
    outputs = history.get("outputs") if isinstance(history, dict) else None
    nodes = list(outputs) if isinstance(outputs, dict) else []
    _write_log({"event": "completed", "mode": mode, "preset": preset, "prompt_id": prompt_id, "prompt_digest": digest, "elapsed_seconds": round(elapsed, 2), "output_nodes": nodes})
    return history


async def generate_templates(names: list[str] | None = None) -> list[Dict[str, Any]]:
    selection = list(WAN_TEMPLATES) if names is None else [name for name in names if name in WAN_TEMPLATES]
    results: list[Dict[str, Any]] = []
    for name in selection:
        results.append(await generate_video("", name))
    return results


async def batch_generate(prompts: list[str], mode: str = "wan", **kwargs: Any) -> list[Dict[str, Any]]:
    tasks = [generate_video(prompt, mode, **kwargs) for prompt in prompts]
    return await asyncio.gather(*tasks)
