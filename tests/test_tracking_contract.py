import ast
import unittest
from pathlib import Path
from typing import Any, Dict


class TrackingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = Path(__file__).resolve().parents[1] / "automation" / "tracking.py"
        cls.source = cls.path.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        outcome = next(
            node
            for node in cls.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_outcome"
        )
        namespace = {"Any": Any, "Dict": Dict}
        exec(compile(ast.Module(body=[outcome], type_ignores=[]), str(cls.path), "exec"), namespace)
        cls.outcome = staticmethod(namespace["_outcome"])

    def test_success_maps_to_finished(self) -> None:
        self.assertEqual(self.outcome({"status": {"status_str": "success"}}), ("FINISHED", None))

    def test_execution_error_maps_to_failed_and_keeps_payload(self) -> None:
        error = {"exception_type": "RuntimeError", "exception_message": "boom"}
        history = {
            "status": {
                "status_str": "error",
                "messages": [["execution_error", error]],
            }
        }
        self.assertEqual(self.outcome(history), ("FAILED", error))

    def test_interruption_maps_to_killed(self) -> None:
        payload = {"node_id": "7"}
        history = {
            "status": {
                "status_str": "error",
                "messages": [["execution_interrupted", payload]],
            }
        }
        self.assertEqual(self.outcome(history), ("KILLED", payload))

    def test_mlflow_runs_are_explicitly_terminated(self) -> None:
        self.assertIn("set_terminated", self.source)
        self.assertIn('"error.json"', self.source)
        self.assertIn('"elapsed_seconds"', self.source)
        self.assertIn('"fps"', self.source)
        self.assertIn('"workflow.json"', self.source)


if __name__ == "__main__":
    unittest.main()
