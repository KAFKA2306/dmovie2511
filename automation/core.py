import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone, time as dt_time
from pathlib import Path
from typing import Any, Dict, Sequence

import httpx
import websockets
from zoneinfo import ZoneInfo

from .workflows import (
    WAN_TEMPLATES,
    load_defaults,
    load_presets,
    load_prompt_components,
    load_prompt_defaults,
    load_prompts,
    load_scheduling,
)
from .tracking import create_session

SCHEDULING_CONFIG = load_scheduling()
WINDOW_CONFIG = SCHEDULING_CONFIG.get("window", {})
SCHEDULING_ENABLED = bool(SCHEDULING_CONFIG.get("enabled", True))
LOCAL_ZONE = datetime.now().astimezone().tzinfo or timezone.utc
TIMEZONE_NAME = SCHEDULING_CONFIG.get("timezone")
if TIMEZONE_NAME and TIMEZONE_NAME != "local":
    SCHEDULE_ZONE = ZoneInfo(TIMEZONE_NAME)
else:
    SCHEDULE_ZONE = LOCAL_ZONE
WINDOW_START = dt_time.fromisoformat(
    WINDOW_CONFIG.get("start_local", SCHEDULING_CONFIG.get("nightly_window_start", "03:00"))
)
WINDOW_END = dt_time.fromisoformat(
    WINDOW_CONFIG.get("end_local", SCHEDULING_CONFIG.get("nightly_window_end", "05:00"))
)
METADATA_PATH = SCHEDULING_CONFIG.get("metadata_log", "ComfyUI/logs/automation_schedule.jsonl")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMFY_ROOT = PROJECT_ROOT / "ComfyUI"
LOG_FILE = COMFY_ROOT / "logs" / "automation_events.jsonl"
SCHEDULE_LOG_FILE = PROJECT_ROOT / METADATA_PATH
SPANS_MIDNIGHT = (WINDOW_END.hour * 60 + WINDOW_END.minute) <= (WINDOW_START.hour * 60 + WINDOW_START.minute)
PROMPTS = load_prompts()
PROMPT_DEFAULTS = load_prompt_defaults()
PROMPT_COMPONENTS = load_prompt_components()
WAN_COMPONENTS = PROMPT_COMPONENTS.get("wan", {})
WAN_SEGMENTS = tuple(WAN_COMPONENTS.get("segments", ()))
WAN_DESCRIPTOR_MAP = WAN_COMPONENTS.get("descriptors", {})
DESCRIPTORS = [
    ("camera_move", tuple(WAN_DESCRIPTOR_MAP.get("camera_moves", ()))),
    ("lighting_style", tuple(WAN_DESCRIPTOR_MAP.get("lighting_styles", ()))),
    ("color_grade", tuple(WAN_DESCRIPTOR_MAP.get("color_grades", ()))),
    ("lens_profile", tuple(WAN_DESCRIPTOR_MAP.get("lens_profiles", ()))),
    ("capture_technique", tuple(WAN_DESCRIPTOR_MAP.get("capture_techniques", ()))),
    ("texture_detail", tuple(WAN_DESCRIPTOR_MAP.get("texture_details", ()))),
    ("post_treatment", tuple(WAN_DESCRIPTOR_MAP.get("post_treatments", ()))),
]
WAN_FALLBACK_KEY = WAN_COMPONENTS.get("fallback_key") or PROMPT_DEFAULTS.get("wan_fallback", "")
WAN_FILLER_KEY = WAN_COMPONENTS.get("filler_key") or PROMPT_DEFAULTS.get("wan_filler", "")
WAN_MIN_WORDS = int(WAN_COMPONENTS.get("min_words", 80))
WAN_MAX_WORDS = int(WAN_COMPONENTS.get("max_words", 120))
WAIT_INTERVAL = int(SCHEDULING_CONFIG.get("waiting_log_interval_seconds", 0))


def _resolve_quantization(model_name: str) -> str:
    name = str(model_name).lower()
    if name.endswith(".gguf"):
        return "disabled"
    return "fp8_e4m3fn_scaled"


def _prompt_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _write_log(payload: Dict[str, Any]) -> None:
    data = dict(payload)
    data["timestamp"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def _collect_output_paths(history: Dict[str, Any]) -> list[str]:
    outputs = history.get("outputs", {})
    paths: list[str] = []
    for node in outputs.values():
        if isinstance(node, dict):
            for artifacts in node.values():
                if isinstance(artifacts, list):
                    for entry in artifacts:
                        if isinstance(entry, dict):
                            fullpath = entry.get("fullpath", "")
                            if not fullpath:
                                filename = entry.get("filename", "")
                                folder = entry.get("type", "")
                                candidate = COMFY_ROOT
                                if folder:
                                    candidate = candidate / folder
                                subfolder = entry.get("subfolder", "")
                                if subfolder:
                                    candidate = candidate / subfolder
                                if filename:
                                    fullpath = str(candidate / filename)
                            if fullpath:
                                resolved = Path(fullpath).resolve()
                                project = PROJECT_ROOT.resolve()
                                resolved_str = str(resolved)
                                project_str = str(project)
                                if resolved_str.startswith(project_str):
                                    rel = resolved_str[len(project_str):]
                                    if rel.startswith("/"):
                                        rel = rel[1:]
                                    if rel and rel not in paths:
                                        paths.append(rel)
                                elif resolved_str not in paths:
                                    paths.append(resolved_str)
    return paths


def _descriptor_index(prompt: str) -> int:
    return sum(ord(ch) for ch in prompt)


def _pick_descriptor(prompt: str, items: Sequence[str], offset: int) -> str:
    if not items:
        return ""
    idx = _descriptor_index(prompt)
    return items[(idx + offset) % len(items)]


def enrich_prompt(base_prompt: str) -> str:
    fallback = PROMPTS.get(WAN_FALLBACK_KEY, "")
    text = base_prompt.strip() or fallback
    descriptor_values: Dict[str, str] = {}
    for idx, (name, options) in enumerate(DESCRIPTORS):
        descriptor_values[name] = _pick_descriptor(text, options, idx)
    segments = [segment.format(prompt=text, **descriptor_values) for segment in WAN_SEGMENTS]
    if not segments:
        prompt = text
    else:
        prompt = " ".join(segments)
    filler = PROMPTS.get(WAN_FILLER_KEY, "")
    words = prompt.split()
    while len(words) < WAN_MIN_WORDS and filler:
        prompt = f"{prompt} {filler}"
        words = prompt.split()
    if len(words) > WAN_MAX_WORDS:
        prompt = " ".join(words[:WAN_MAX_WORDS])
    return prompt


def _utc_stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _write_schedule_log(payload: Dict[str, Any]) -> None:
    data = dict(payload)
    data["timestamp"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    SCHEDULE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SCHEDULE_LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def _current_time() -> datetime:
    if SCHEDULE_ZONE:
        return datetime.now(SCHEDULE_ZONE)
    return datetime.now().astimezone()


def _window_anchor(moment: datetime, anchor: dt_time) -> datetime:
    return moment.replace(hour=anchor.hour, minute=anchor.minute, second=anchor.second, microsecond=0)


def _within_window(moment: datetime) -> bool:
    minutes = moment.hour * 60 + moment.minute
    start = WINDOW_START.hour * 60 + WINDOW_START.minute
    end = WINDOW_END.hour * 60 + WINDOW_END.minute
    if start == end:
        return True
    if SPANS_MIDNIGHT:
        return minutes >= start or minutes < end
    return start <= minutes < end


def _current_window_start(moment: datetime) -> datetime:
    start = _window_anchor(moment, WINDOW_START)
    if SPANS_MIDNIGHT and moment.hour * 60 + moment.minute < WINDOW_END.hour * 60 + WINDOW_END.minute:
        start -= timedelta(days=1)
    if not SPANS_MIDNIGHT and moment < start:
        start -= timedelta(days=1)
    return start


def _next_window_start(moment: datetime) -> datetime:
    if _within_window(moment):
        return _current_window_start(moment)
    start = _window_anchor(moment, WINDOW_START)
    if SPANS_MIDNIGHT:
        if moment.hour * 60 + moment.minute < WINDOW_END.hour * 60 + WINDOW_END.minute:
            return start
        if start <= moment:
            return start + timedelta(days=1)
        return start
    if moment < start:
        return start
    return start + timedelta(days=1)


async def _align_to_window(
    mode: str,
    preset: str | None,
    digest: str,
    words: int,
    prompt: str,
    schedule_mode: str,
    parameters: Dict[str, Any],
) -> datetime:
    now = _current_time()
    if _within_window(now):
        window_start = _current_window_start(now)
        _write_schedule_log(
            {
                "event": "window_active",
                "mode": mode,
                "preset": preset,
                "prompt_digest": digest,
                "window_start_local": window_start.isoformat(timespec="seconds"),
                "window_start_utc": _utc_stamp(window_start),
                "words": words,
                "schedule_mode": schedule_mode,
                "prompt": prompt,
                "parameters": parameters,
            }
        )
        return window_start
    window_start = _next_window_start(now)
    _write_schedule_log(
        {
            "event": "scheduled",
            "mode": mode,
            "preset": preset,
            "prompt_digest": digest,
            "window_start_local": window_start.isoformat(timespec="seconds"),
            "window_start_utc": _utc_stamp(window_start),
            "words": words,
            "schedule_mode": schedule_mode,
            "prompt": prompt,
            "parameters": parameters,
        }
    )
    delay = (window_start - now).total_seconds()
    if delay > 0:
        if WAIT_INTERVAL > 0:
            remaining = delay
            while remaining > WAIT_INTERVAL:
                await asyncio.sleep(WAIT_INTERVAL)
                remaining -= WAIT_INTERVAL
                _write_schedule_log(
                    {
                        "event": "awaiting_window",
                        "mode": mode,
                        "preset": preset,
                        "prompt_digest": digest,
                        "window_start_local": window_start.isoformat(timespec="seconds"),
                        "window_start_utc": _utc_stamp(window_start),
                        "words": words,
                        "time_remaining_seconds": round(remaining, 2),
                        "schedule_mode": schedule_mode,
                        "prompt": prompt,
                        "parameters": parameters,
                    }
                )
                await asyncio.sleep(remaining)
            else:
                await asyncio.sleep(delay)
    _write_schedule_log(
        {
            "event": "window_open",
            "mode": mode,
            "preset": preset,
            "prompt_digest": digest,
            "window_start_local": window_start.isoformat(timespec="seconds"),
            "window_start_utc": _utc_stamp(window_start),
            "words": words,
            "schedule_mode": schedule_mode,
            "prompt": prompt,
            "parameters": parameters,
        }
    )
    return window_start


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
            return data["prompt_id"]

    async def wait_for_completion(self, prompt_id: str, context: Dict[str, Any] | None = None) -> None:
        base = dict(context or {})
        base["prompt_id"] = prompt_id

        def write(event: str, details: Dict[str, Any]) -> None:
            payload = dict(base)
            payload.update(details)
            payload["event"] = event
            _write_log(payload)

        async with websockets.connect(f"{self.ws_url}?clientId={self.client_id}") as ws:
            while True:
                packet = await ws.recv()
                if isinstance(packet, bytes):
                    continue
                msg = json.loads(packet)
                kind = msg.get("type")
                data = msg.get("data") or {}
                data_prompt = data.get("prompt_id")
                if data_prompt and data_prompt != prompt_id:
                    continue
                if kind == "execution_start":
                    write("execution_start", {})
                    print("execution start")
                elif kind == "execution_cached":
                    nodes = data.get("nodes") or []
                    write("execution_cached", {"nodes": nodes})
                elif kind == "executing":
                    node = data.get("display_node") or data.get("node")
                    if node is None:
                        write("execution_complete", {})
                        print("execution complete")
                        break
                    write("node_executing", {"node": node})
                    print(f"{node} executing")
                elif kind == "progress":
                    node = data.get("node")
                    value = data.get("value")
                    maximum = data.get("max")
                    write("node_progress", {"node": node, "value": value, "max": maximum})
                    if node is not None and value is not None and maximum is not None:
                        print(f"{node} progress {value}/{maximum}")
                elif kind == "execution_error":
                    message = data.get("exception_message") or ""
                    write("execution_error", {"message": message})
                    print(f"execution error {message}")
                    break
                elif kind == "execution_interrupted":
                    write("execution_interrupted", {})
                    print("execution interrupted")
                    break

    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.http_url}/history/{prompt_id}")
            data = resp.json()
            return data[prompt_id]


def build_wan_workflow(prompt: str, **kwargs: Any) -> tuple[Dict[str, Any], Dict[str, Any]]:
    explicit_quantization = "quantization" in kwargs and kwargs.get("quantization") is not None
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
    model_name = kwargs.get("model_name", "Wan2.2-Animate-14B-Q5_K_M.gguf")
    quantization = kwargs.get("quantization")
    if not explicit_quantization or quantization is None:
        quantization = _resolve_quantization(model_name)
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
    parameters = {
        "seed": seed,
        "quality_mode": quality_mode,
        "steps": steps,
        "cfg": cfg,
        "dual_pass_cfg": dual_pass_cfg,
        "width": width,
        "height": height,
        "frames": frames,
        "frame_rate": frame_rate,
        "text_encoder_name": text_encoder_name,
        "model_name": model_name,
        "quantization": quantization,
        "vae_name": vae_name,
        "filename_prefix": filename_prefix,
        "negative_prompt": negative_prompt,
        "stage_one_scheduler": stage_one_scheduler,
        "stage_two_scheduler": stage_two_scheduler,
        "dual_stage_enabled": dual_stage_enabled,
        "stage_one_steps": stage_one_steps,
        "stage_two_steps": stage_two_steps,
        "dual_stage_denoise": dual_stage_denoise,
    }
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
                "quantization": quantization,
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
    return workflow, parameters


async def generate_video(prompt: str, mode: str = "wan", **kwargs: Any) -> Dict[str, Any]:
    client = ComfyUIClient()
    options = dict(kwargs)
    use_schedule_flag = options.pop("use_schedule", None)
    preset = options.get("preset")
    parameters_snapshot = dict(options)
    used_prompt = prompt
    workflow: Dict[str, Any]
    workflow_parameters: Dict[str, Any]
    enriched_prompt = used_prompt
    if mode == "wan":
        enriched_prompt = enrich_prompt(used_prompt)
        workflow, workflow_parameters = build_wan_workflow(enriched_prompt, **options)
    else:
        template = WAN_TEMPLATES.get(mode)
        if template:
            data = template.copy()
            data.update(options)
            template_prompt = data.pop("prompt", "")
            used_prompt = prompt or template_prompt
            enriched_prompt = enrich_prompt(used_prompt)
            workflow, workflow_parameters = build_wan_workflow(enriched_prompt, **data)
        else:
            workflow = {}
            workflow_parameters = {}
    digest = _prompt_digest(used_prompt)
    words = len(used_prompt.split())
    schedule_active = SCHEDULING_ENABLED if use_schedule_flag is None else bool(use_schedule_flag)
    schedule_mode = "window" if schedule_active else "immediate"
    tracking_parameters = dict(workflow_parameters)
    for key, value in parameters_snapshot.items():
        tracking_parameters.setdefault(key, value)
    tracking_session = create_session(
        mode=mode,
        preset=preset,
        digest=digest,
        prompt=used_prompt,
        enriched_prompt=enriched_prompt,
        parameters=tracking_parameters,
        workflow=workflow,
        schedule_mode=schedule_mode,
    )
    if schedule_active:
        window_start = await _align_to_window(
            mode,
            preset,
            digest,
            words,
            used_prompt,
            schedule_mode,
            parameters_snapshot,
        )
    else:
        window_start = _current_time()
        _write_schedule_log(
            {
                "event": "schedule_immediate",
                "mode": mode,
                "preset": preset,
                "prompt_digest": digest,
                "window_start_local": window_start.isoformat(timespec="seconds"),
                "window_start_utc": _utc_stamp(window_start),
                "words": words,
                "schedule_mode": schedule_mode,
                "prompt": used_prompt,
                "parameters": parameters_snapshot,
            }
        )
    tracking_session.log_window(window_start)
    start_time = datetime.utcnow()
    tracking_session.set_start(start_time)
    _write_schedule_log(
        {
            "event": "execution_started",
            "mode": mode,
            "preset": preset,
            "prompt_digest": digest,
            "window_start_local": window_start.isoformat(timespec="seconds"),
            "window_start_utc": _utc_stamp(window_start),
            "words": words,
            "schedule_mode": schedule_mode,
        }
    )
    _write_log(
        {
            "event": "queue_start",
            "mode": mode,
            "preset": preset,
            "prompt_digest": digest,
            "words": words,
            "schedule_mode": schedule_mode,
        }
    )
    prompt_id = await client.queue_prompt(workflow)
    tracking_session.log_queue(prompt_id)
    _write_log(
        {
            "event": "queued",
            "mode": mode,
            "preset": preset,
            "prompt_id": prompt_id,
            "prompt_digest": digest,
            "schedule_mode": schedule_mode,
        }
    )
    wait_context = {
        "mode": mode,
        "preset": preset,
        "prompt_digest": digest,
        "schedule_mode": schedule_mode,
    }
    await client.wait_for_completion(prompt_id, wait_context)
    history = await client.get_history(prompt_id)
    end_time = datetime.utcnow()
    elapsed = (end_time - start_time).total_seconds()
    outputs = history.get("outputs") if isinstance(history, dict) else None
    nodes = list(outputs) if isinstance(outputs, dict) else []
    paths = _collect_output_paths(history) if isinstance(history, dict) else []
    history_payload = history if isinstance(history, dict) else {}
    tracking_session.log_completion(
        elapsed,
        end_time,
        nodes,
        paths,
        history_payload,
    )
    _write_log(
        {
            "event": "completed",
            "mode": mode,
            "preset": preset,
            "prompt_id": prompt_id,
            "prompt_digest": digest,
            "elapsed_seconds": round(elapsed, 2),
            "output_nodes": nodes,
            "output_paths": paths,
            "schedule_mode": schedule_mode,
        }
    )
    _write_schedule_log(
        {
            "event": "execution_completed",
            "mode": mode,
            "preset": preset,
            "prompt_digest": digest,
            "elapsed_seconds": round(elapsed, 2),
            "window_start_local": window_start.isoformat(timespec="seconds"),
            "window_start_utc": _utc_stamp(window_start),
            "words": words,
            "schedule_mode": schedule_mode,
        }
    )
    return history


async def generate_templates(names: list[str] | None = None) -> list[Dict[str, Any]]:
    selection = list(WAN_TEMPLATES) if names is None else [name for name in names if name in WAN_TEMPLATES]
    results: list[Dict[str, Any]] = []
    for name in selection:
        results.append(await generate_video("", name))
    return results


async def batch_generate(prompts: list[str], mode: str = "wan", **kwargs: Any) -> list[Dict[str, Any]]:
    results: list[Dict[str, Any]] = []
    for prompt in prompts:
        results.append(await generate_video(prompt, mode, **kwargs))
    return results


def pending_scheduled_jobs() -> list[Dict[str, Any]]:
    if not SCHEDULE_LOG_FILE.exists():
        return []
    lines = SCHEDULE_LOG_FILE.read_text(encoding="utf-8").splitlines()
    entries: list[Dict[str, Any]] = []
    for line in lines:
        if line:
            entries.append(json.loads(line))
    pending_map: dict[str, Dict[str, Any]] = {}
    order: list[str] = []
    for entry in entries:
        digest = entry.get("prompt_digest")
        if not digest:
            continue
        event = entry.get("event")
        if event in {"execution_started", "execution_completed"}:
            if digest in pending_map:
                del pending_map[digest]
            if digest in order:
                order.remove(digest)
            continue
        if event == "schedule_immediate":
            if digest in pending_map:
                del pending_map[digest]
            if digest in order:
                order.remove(digest)
            continue
        if event in {"scheduled", "awaiting_window", "window_open", "window_active"}:
            pending_map[digest] = entry
            if digest not in order:
                order.append(digest)
    pending: list[Dict[str, Any]] = []
    for digest in order:
        entry = pending_map.get(digest)
        if entry:
            pending.append(entry)
    return sorted(pending, key=lambda item: item.get("window_start_utc", item.get("timestamp", "")))


async def run_scheduled_jobs(entries: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    results: list[Dict[str, Any]] = []
    for entry in entries:
        parameters = dict(entry.get("parameters", {}))
        preset = entry.get("preset")
        if preset and "preset" not in parameters:
            parameters["preset"] = preset
        parameters["use_schedule"] = False
        mode = entry.get("mode", "wan")
        prompt = entry.get("prompt", "")
        results.append(await generate_video(prompt, mode, **parameters))
    return results
