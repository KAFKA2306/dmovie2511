import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from mlflow.entities import Run
from mlflow.tracking import MlflowClient
import torch

from .workflows import load_tracking

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG = load_tracking()
ENABLED = bool(CONFIG.get("enabled", False))
ARTIFACT_DIR = CONFIG.get("artifact_dir", "ComfyUI/logs/mlruns")
EXPERIMENT_NAME = CONFIG.get("experiment_name", "wan_automation")
RUN_NAME_PATTERN = CONFIG.get("run_name", "{mode}-{digest}-{stamp}")
UI_HOST = CONFIG.get("ui_host", "127.0.0.1")
UI_PORT = int(CONFIG.get("ui_port", 8250))
LIST_LIMIT = int(CONFIG.get("list_limit", 20))

CLIENT: MlflowClient | None = None
EXPERIMENT_ID: str | None = None
TRACKING_URI: str | None = None


def _utc_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _local_iso(moment: datetime) -> str:
    return moment.astimezone().isoformat()


def _tracking_path() -> Path:
    path = PROJECT_ROOT / ARTIFACT_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def _client() -> Tuple[MlflowClient, str, str]:
    global CLIENT, EXPERIMENT_ID, TRACKING_URI
    if CLIENT is not None and EXPERIMENT_ID is not None and TRACKING_URI is not None:
        return CLIENT, EXPERIMENT_ID, TRACKING_URI
    path = _tracking_path()
    uri = path.as_uri()
    client = MlflowClient(tracking_uri=uri)
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment:
        experiment_id = experiment.experiment_id
    else:
        experiment_id = client.create_experiment(EXPERIMENT_NAME)
    CLIENT = client
    EXPERIMENT_ID = experiment_id
    TRACKING_URI = uri
    return client, experiment_id, uri


def _stringify_params(values: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for key, value in values.items():
        if isinstance(value, (dict, list, tuple, set)):
            result[key] = json.dumps(value, ensure_ascii=False)
        else:
            result[key] = str(value)
    return result


def _gpu_tags() -> Dict[str, str]:
    if not torch.cuda.is_available():
        return {
            "gpu_available": "false",
        }
    count = torch.cuda.device_count()
    tags: Dict[str, str] = {
        "gpu_available": "true",
        "gpu_device_count": str(count),
    }
    if count > 0:
        name = torch.cuda.get_device_name(0)
        total = torch.cuda.get_device_properties(0).total_memory
        tags["gpu_primary_name"] = name
        tags["gpu_primary_total_vram_bytes"] = str(total)
    return tags


class NullSession:
    def log_window(self, window_start: datetime) -> None:
        return

    def set_start(self, moment: datetime) -> None:
        return

    def log_queue(self, prompt_id: str) -> None:
        return

    def log_completion(
        self,
        elapsed: float,
        end_time: datetime,
        nodes: Sequence[str],
        paths: Sequence[str],
        history: Dict[str, Any],
    ) -> None:
        return


class TrackingSession:
    def __init__(
        self,
        mode: str,
        preset: str | None,
        digest: str,
        prompt: str,
        enriched_prompt: str,
        parameters: Dict[str, Any],
        workflow: Dict[str, Any],
        schedule_mode: str,
    ) -> None:
        client, experiment_id, _ = _client()
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        run_name = RUN_NAME_PATTERN.format(
            mode=mode,
            preset=preset or "none",
            digest=digest,
            stamp=stamp,
        )
        tags = {
            "mode": mode,
            "preset": preset or "",
            "prompt_digest": digest,
            "schedule_mode": schedule_mode,
            "prompt_words": str(len(enriched_prompt.split())),
        }
        tags.update(_gpu_tags())
        run = client.create_run(
            experiment_id=experiment_id,
            tags=tags,
            run_name=run_name,
        )
        self.client = client
        self.run_id = run.info.run_id
        self.parameters = parameters
        for key, value in _stringify_params(parameters).items():
            self.client.log_param(self.run_id, key, value)
        self.client.log_text(self.run_id, prompt, "prompt_input.txt")
        self.client.log_text(self.run_id, enriched_prompt, "prompt_enriched.txt")
        self.client.log_dict(self.run_id, workflow, "workflow.json")
        self.start_time: datetime | None = None

    def log_window(self, window_start: datetime) -> None:
        self.client.set_tag(self.run_id, "window_start_utc", _utc_iso(window_start))
        self.client.set_tag(self.run_id, "window_start_local", _local_iso(window_start))

    def set_start(self, moment: datetime) -> None:
        utc_start = moment.replace(tzinfo=timezone.utc)
        self.start_time = utc_start
        self.client.set_tag(self.run_id, "execution_start_utc", _utc_iso(utc_start))

    def log_queue(self, prompt_id: str) -> None:
        self.client.set_tag(self.run_id, "prompt_id", prompt_id)

    def log_completion(
        self,
        elapsed: float,
        end_time: datetime,
        nodes: Sequence[str],
        paths: Sequence[str],
        history: Dict[str, Any],
    ) -> None:
        utc_end = end_time.replace(tzinfo=timezone.utc)
        frames_value = float(self.parameters.get("frames", 0) or 0)
        fps = frames_value / elapsed if elapsed > 0 and frames_value else 0.0
        self.client.log_metric(self.run_id, "elapsed_seconds", elapsed)
        if fps:
            self.client.log_metric(self.run_id, "fps", fps)
        self.client.set_tag(self.run_id, "execution_end_utc", _utc_iso(utc_end))
        if self.start_time:
            self.client.set_tag(self.run_id, "execution_start_epoch", str(int(self.start_time.timestamp())))
        self.client.set_tag(self.run_id, "execution_end_epoch", str(int(utc_end.timestamp())))
        self.client.set_tag(self.run_id, "output_nodes", ",".join(nodes))
        self.client.set_tag(
            self.run_id,
            "output_paths",
            json.dumps([str(path) for path in paths], ensure_ascii=False),
        )
        self.client.log_dict(self.run_id, history, "history.json")
        for path in paths:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = PROJECT_ROOT / path
            if file_path.exists():
                self.client.log_artifact(self.run_id, str(file_path))


def create_session(
    mode: str,
    preset: str | None,
    digest: str,
    prompt: str,
    enriched_prompt: str,
    parameters: Dict[str, Any],
    workflow: Dict[str, Any],
    schedule_mode: str,
) -> NullSession | TrackingSession:
    if not ENABLED:
        return NullSession()
    return TrackingSession(
        mode=mode,
        preset=preset,
        digest=digest,
        prompt=prompt,
        enriched_prompt=enriched_prompt,
        parameters=parameters,
        workflow=workflow,
        schedule_mode=schedule_mode,
    )


def _format_run_line(run: Run) -> str:
    data = run.data
    start_ms = run.info.start_time or 0
    start = datetime.fromtimestamp(start_ms / 1000, timezone.utc)
    elapsed = data.metrics.get("elapsed_seconds", 0.0)
    mode = data.tags.get("mode", "")
    preset = data.tags.get("preset", "")
    prompt_digest = data.tags.get("prompt_digest", "")
    return f"{run.info.run_id} | {start.isoformat()} | {mode} | {preset} | {elapsed:.2f}s | {prompt_digest}"


def _print_run_paths(run: Run) -> None:
    paths = run.data.tags.get("output_paths")
    if not paths:
        return
    decoded = json.loads(paths)
    for entry in decoded:
        print(f"  artifact: {entry}")


def _list_runs(client: MlflowClient, experiment_id: str) -> None:
    runs = client.search_runs(
        experiment_ids=[experiment_id],
        order_by=["attributes.start_time DESC"],
        max_results=LIST_LIMIT,
    )
    if not runs:
        print("No experiments.")
        return
    for run in runs:
        print(_format_run_line(run))
        _print_run_paths(run)


def _stats(client: MlflowClient, experiment_id: str) -> None:
    runs = client.search_runs(
        experiment_ids=[experiment_id],
        order_by=["attributes.start_time DESC"],
        max_results=LIST_LIMIT,
    )
    if not runs:
        print("No experiments.")
        return
    durations = [run.data.metrics.get("elapsed_seconds", 0.0) for run in runs if run.data.metrics.get("elapsed_seconds")]
    if durations:
        avg = sum(durations) / len(durations)
        print(f"Average elapsed_seconds: {avg:.2f}")
        print(f"Min elapsed_seconds: {min(durations):.2f}")
        print(f"Max elapsed_seconds: {max(durations):.2f}")
    presets: Dict[str, List[float]] = {}
    for run in runs:
        preset = run.data.tags.get("preset") or "default"
        if run.data.metrics.get("elapsed_seconds"):
            presets.setdefault(preset, []).append(run.data.metrics["elapsed_seconds"])
    for preset, values in presets.items():
        avg = sum(values) / len(values)
        print(f"{preset}: count={len(values)} avg={avg:.2f}")


def _compare(client: MlflowClient, run_ids: Sequence[str]) -> None:
    if len(run_ids) < 2:
        print("Need two run ids.")
        return
    run_a = client.get_run(run_ids[0])
    run_b = client.get_run(run_ids[1])
    keys = sorted(set(run_a.data.params) | set(run_b.data.params))
    print(f"Comparing {run_ids[0]} vs {run_ids[1]}")
    for key in keys:
        left = run_a.data.params.get(key, "-")
        right = run_b.data.params.get(key, "-")
        marker = "!=" if left != right else "=="
        print(f"{key}: {left} {marker} {right}")
    metric_keys = sorted(set(run_a.data.metrics) | set(run_b.data.metrics))
    for key in metric_keys:
        left = run_a.data.metrics.get(key, "-")
        right = run_b.data.metrics.get(key, "-")
        marker = "!=" if left != right else "=="
        print(f"{key}: {left} {marker} {right}")


def handle_cli(args: Sequence[str]) -> None:
    if not ENABLED:
        print("Tracking disabled.")
        return
    client, experiment_id, uri = _client()
    if not args:
        subprocess.run([
            "uv",
            "run",
            "mlflow",
            "ui",
            "--backend-store-uri",
            uri,
            "--default-artifact-root",
            uri,
            "--host",
            UI_HOST,
            "--port",
            str(UI_PORT),
        ])
        return
    head = args[0]
    tail = args[1:]
    if head == "--list":
        _list_runs(client, experiment_id)
        return
    if head == "--stats":
        _stats(client, experiment_id)
        return
    if head == "--compare":
        _compare(client, tail)
        return
    if head == "--artifacts" and tail:
        run = client.get_run(tail[0])
        _print_run_paths(run)
        return
    print("Unknown experiments command.")
