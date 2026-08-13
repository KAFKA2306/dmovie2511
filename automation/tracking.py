import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import torch
from mlflow.entities import Run
from mlflow.tracking import MlflowClient

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
    uri = _tracking_path().as_uri()
    client = MlflowClient(tracking_uri=uri)
    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
    experiment_id = experiment.experiment_id if experiment else client.create_experiment(EXPERIMENT_NAME)
    CLIENT = client
    EXPERIMENT_ID = experiment_id
    TRACKING_URI = uri
    return client, experiment_id, uri


def _stringify_params(values: Dict[str, Any]) -> Dict[str, str]:
    return {
        key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, tuple, set)) else str(value)
        for key, value in values.items()
    }


def _gpu_tags() -> Dict[str, str]:
    if not torch.cuda.is_available():
        return {"gpu_available": "false"}
    tags = {
        "gpu_available": "true",
        "gpu_device_count": str(torch.cuda.device_count()),
    }
    if torch.cuda.device_count():
        tags["gpu_primary_name"] = torch.cuda.get_device_name(0)
        tags["gpu_primary_total_vram_bytes"] = str(torch.cuda.get_device_properties(0).total_memory)
    return tags


def _outcome(history: Dict[str, Any]) -> tuple[str, Dict[str, Any] | None]:
    status = history.get("status") or {}
    if status.get("status_str") != "error":
        return "FINISHED", None
    payload = None
    interrupted = False
    for entry in status.get("messages") or []:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        event, data = entry[0], entry[1]
        if event == "execution_error" and isinstance(data, dict):
            payload = data
        if event == "execution_interrupted":
            interrupted = True
            if isinstance(data, dict):
                payload = data
    return ("KILLED" if interrupted else "FAILED"), payload


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
        run_name = RUN_NAME_PATTERN.format(
            mode=mode,
            preset=preset or "none",
            digest=digest,
            stamp=datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
        )
        tags = {
            "mode": mode,
            "preset": preset or "",
            "prompt_digest": digest,
            "schedule_mode": schedule_mode,
            "prompt_words": str(len(enriched_prompt.split())),
        }
        tags.update(_gpu_tags())
        run = client.create_run(experiment_id=experiment_id, tags=tags, run_name=run_name)
        self.client = client
        self.run_id = run.info.run_id
        self.parameters = parameters
        for key, value in _stringify_params(parameters).items():
            client.log_param(self.run_id, key, value)
        client.log_text(self.run_id, prompt, "prompt_input.txt")
        client.log_text(self.run_id, enriched_prompt, "prompt_enriched.txt")
        client.log_dict(self.run_id, workflow, "workflow.json")
        self.start_time: datetime | None = None

    def log_window(self, window_start: datetime) -> None:
        self.client.set_tag(self.run_id, "window_start_utc", _utc_iso(window_start))
        self.client.set_tag(self.run_id, "window_start_local", _local_iso(window_start))

    def set_start(self, moment: datetime) -> None:
        self.start_time = moment.replace(tzinfo=timezone.utc)
        self.client.set_tag(self.run_id, "execution_start_utc", _utc_iso(self.start_time))

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
        frames = float(self.parameters.get("frames", 0) or 0)
        self.client.log_metric(self.run_id, "elapsed_seconds", elapsed)
        if elapsed > 0 and frames:
            self.client.log_metric(self.run_id, "fps", frames / elapsed)
        self.client.set_tag(self.run_id, "execution_end_utc", _utc_iso(utc_end))
        if self.start_time:
            self.client.set_tag(self.run_id, "execution_start_epoch", str(int(self.start_time.timestamp())))
        self.client.set_tag(self.run_id, "execution_end_epoch", str(int(utc_end.timestamp())))
        self.client.set_tag(self.run_id, "output_nodes", ",".join(nodes))
        self.client.set_tag(self.run_id, "output_paths", json.dumps(list(paths), ensure_ascii=False))
        self.client.log_dict(self.run_id, history, "history.json")
        for path in paths:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = PROJECT_ROOT / file_path
            if file_path.exists():
                self.client.log_artifact(self.run_id, str(file_path))
        status, error = _outcome(history)
        if error:
            self.client.log_dict(self.run_id, error, "error.json")
            self.client.set_tag(self.run_id, "error_type", str(error.get("exception_type", "")))
            self.client.set_tag(self.run_id, "error_message", str(error.get("exception_message", "")))
        self.client.set_terminated(self.run_id, status=status)


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
    start = datetime.fromtimestamp((run.info.start_time or 0) / 1000, timezone.utc)
    data = run.data
    return (
        f"{run.info.run_id} | {start.isoformat()} | {data.tags.get('mode', '')} | "
        f"{data.tags.get('preset', '')} | {data.metrics.get('elapsed_seconds', 0.0):.2f}s | "
        f"{data.tags.get('prompt_digest', '')}"
    )


def _print_run_paths(run: Run) -> None:
    for entry in json.loads(run.data.tags.get("output_paths") or "[]"):
        print(f"  artifact: {entry}")


def _runs(client: MlflowClient, experiment_id: str) -> List[Run]:
    return list(
        client.search_runs(
            experiment_ids=[experiment_id],
            order_by=["attributes.start_time DESC"],
            max_results=LIST_LIMIT,
        )
    )


def _list_runs(client: MlflowClient, experiment_id: str) -> None:
    runs = _runs(client, experiment_id)
    if not runs:
        print("No experiments.")
        return
    for run in runs:
        print(_format_run_line(run))
        _print_run_paths(run)


def _stats(client: MlflowClient, experiment_id: str) -> None:
    runs = _runs(client, experiment_id)
    durations = [run.data.metrics["elapsed_seconds"] for run in runs if "elapsed_seconds" in run.data.metrics]
    if not durations:
        print("No experiments.")
        return
    print(f"Average elapsed_seconds: {sum(durations) / len(durations):.2f}")
    print(f"Min elapsed_seconds: {min(durations):.2f}")
    print(f"Max elapsed_seconds: {max(durations):.2f}")
    presets: Dict[str, List[float]] = {}
    for run in runs:
        if "elapsed_seconds" in run.data.metrics:
            presets.setdefault(run.data.tags.get("preset") or "default", []).append(run.data.metrics["elapsed_seconds"])
    for preset, values in presets.items():
        print(f"{preset}: count={len(values)} avg={sum(values) / len(values):.2f}")


def _compare(client: MlflowClient, run_ids: Sequence[str]) -> None:
    if len(run_ids) < 2:
        print("Need two run ids.")
        return
    left = client.get_run(run_ids[0])
    right = client.get_run(run_ids[1])
    print(f"Comparing {run_ids[0]} vs {run_ids[1]}")
    for key in sorted(set(left.data.params) | set(right.data.params)):
        a = left.data.params.get(key, "-")
        b = right.data.params.get(key, "-")
        print(f"{key}: {a} {'!=' if a != b else '=='} {b}")
    for key in sorted(set(left.data.metrics) | set(right.data.metrics)):
        a = left.data.metrics.get(key, "-")
        b = right.data.metrics.get(key, "-")
        print(f"{key}: {a} {'!=' if a != b else '=='} {b}")


def handle_cli(args: Sequence[str]) -> None:
    if not ENABLED:
        print("Tracking disabled.")
        return
    client, experiment_id, uri = _client()
    if not args:
        subprocess.run(
            [
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
            ],
            check=False,
        )
        return
    head, *tail = args
    if head == "--list":
        _list_runs(client, experiment_id)
    elif head == "--stats":
        _stats(client, experiment_id)
    elif head == "--compare":
        _compare(client, tail)
    elif head == "--artifacts" and tail:
        _print_run_paths(client.get_run(tail[0]))
    else:
        print("Unknown experiments command.")
