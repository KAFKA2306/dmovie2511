import asyncio
import json
import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo


class _TrackingSession:
    def log_window(self, *_args, **_kwargs):
        return None

    def set_start(self, *_args, **_kwargs):
        return None

    def log_queue(self, *_args, **_kwargs):
        return None

    def log_completion(self, *_args, **_kwargs):
        return None


tracking_stub = types.ModuleType("automation.tracking")
tracking_stub.create_session = lambda **_kwargs: _TrackingSession()
sys.modules.setdefault("automation.tracking", tracking_stub)

from automation import core  # noqa: E402


class SchedulerContractTests(unittest.IsolatedAsyncioTestCase):
    def test_scheduler_is_enabled_with_expected_window(self):
        self.assertTrue(core.SCHEDULING_ENABLED)
        self.assertEqual(core.WINDOW_START.isoformat(timespec="minutes"), "03:00")
        self.assertEqual(core.WINDOW_END.isoformat(timespec="minutes"), "05:00")
        self.assertEqual(str(core.SCHEDULE_ZONE), "Asia/Tokyo")
        self.assertEqual(core.WAIT_INTERVAL, 0)
        self.assertEqual(core.METADATA_PATH, "ComfyUI/logs/automation_schedule.jsonl")

    async def test_daytime_job_is_reserved_before_single_wait(self):
        zone = ZoneInfo("Asia/Tokyo")
        now = datetime(2026, 8, 13, 20, 0, tzinfo=zone)
        expected_window = datetime(2026, 8, 14, 3, 0, tzinfo=zone)
        logs = []
        sleep = AsyncMock()

        with (
            patch.object(core, "_current_time", return_value=now),
            patch.object(core, "_write_schedule_log", side_effect=logs.append),
            patch.object(core.asyncio, "sleep", sleep),
        ):
            window = await core._align_to_window(
                mode="wan",
                preset="standard",
                digest="abc123",
                job_id="job-1",
                words=2,
                prompt="test prompt",
                schedule_mode="window",
                parameters={"preset": "standard"},
            )

        self.assertEqual(window, expected_window)
        self.assertEqual([entry["event"] for entry in logs], ["scheduled", "window_open"])
        self.assertEqual(logs[0]["prompt_digest"], "abc123")
        self.assertTrue(all(entry["job_id"] == "job-1" for entry in logs))
        self.assertEqual(logs[0]["window_start_local"], expected_window.isoformat(timespec="seconds"))
        self.assertEqual(logs[0]["window_start_utc"], "2026-08-13T18:00:00Z")
        sleep.assert_awaited_once_with(7 * 60 * 60)

    async def test_execution_logs_share_unique_job_id(self):
        zone = ZoneInfo("Asia/Tokyo")
        window = datetime(2026, 8, 14, 3, 0, tzinfo=zone)
        logs = []

        class FakeClient:
            async def queue_prompt(self, _workflow):
                return "prompt-1"

            async def wait_for_completion(self, _prompt_id, _context=None):
                return None

            async def get_history(self, _prompt_id):
                return {"outputs": {}}

        with (
            patch.object(core, "ComfyUIClient", return_value=FakeClient()),
            patch.object(core, "_align_to_window", AsyncMock(return_value=window)),
            patch.object(core, "_write_schedule_log", side_effect=logs.append),
            patch.object(core, "_write_log"),
            patch.object(core, "create_session", return_value=_TrackingSession()),
        ):
            await core.generate_video("test prompt", "wan", preset="standard", use_schedule=True)

        events = [entry for entry in logs if entry["event"].startswith("execution_")]
        self.assertEqual([entry["event"] for entry in events], ["execution_started", "execution_completed"])
        self.assertEqual(events[0]["prompt_digest"], events[1]["prompt_digest"])
        self.assertEqual(events[0]["job_id"], events[1]["job_id"])
        self.assertTrue(events[0]["job_id"])
        self.assertEqual(events[0]["window_start_local"], events[1]["window_start_local"])

    def test_same_prompt_can_have_multiple_pending_jobs(self):
        entries = [
            {
                "event": "scheduled",
                "job_id": "job-a",
                "prompt_digest": "same-digest",
                "window_start_utc": "2026-08-13T18:00:00Z",
            },
            {
                "event": "scheduled",
                "job_id": "job-b",
                "prompt_digest": "same-digest",
                "window_start_utc": "2026-08-13T18:00:00Z",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "schedule.jsonl"
            log_path.write_text("\n".join(json.dumps(entry) for entry in entries) + "\n", encoding="utf-8")
            with patch.object(core, "SCHEDULE_LOG_FILE", log_path):
                pending = core.pending_scheduled_jobs()

        self.assertEqual([entry["job_id"] for entry in pending], ["job-a", "job-b"])

    async def test_run_now_preserves_reserved_job_id(self):
        entry = {
            "event": "scheduled",
            "job_id": "job-a",
            "prompt_digest": "same-digest",
            "mode": "wan",
            "prompt": "same prompt",
            "parameters": {"preset": "standard"},
        }
        generate = AsyncMock(return_value={"outputs": {}})
        with patch.object(core, "generate_video", generate):
            await core.run_scheduled_jobs([entry])

        generate.assert_awaited_once_with(
            "same prompt",
            "wan",
            preset="standard",
            use_schedule=False,
            job_id="job-a",
        )

    async def test_batch_generation_is_strictly_sequential(self):
        order = []

        async def fake_generate(prompt, _mode="wan", **_kwargs):
            order.append(f"start:{prompt}")
            await asyncio.sleep(0)
            order.append(f"end:{prompt}")
            return {"prompt": prompt}

        with patch.object(core, "generate_video", side_effect=fake_generate):
            result = await core.batch_generate(["first", "second"], "wan")

        self.assertEqual(order, ["start:first", "end:first", "start:second", "end:second"])
        self.assertEqual(result, [{"prompt": "first"}, {"prompt": "second"}])


if __name__ == "__main__":
    unittest.main()
