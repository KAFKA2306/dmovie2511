import json
import unittest

from automation.core import build_wan_workflow
from automation.workflows import load_defaults, load_presets


class WanDtypeContractTest(unittest.TestCase):
    def test_defaults_do_not_emit_fp64(self):
        workflow, parameters = build_wan_workflow(
            "contract fixture", **load_defaults()
        )
        payload = json.dumps(workflow, sort_keys=True).lower()
        self.assertNotIn("float64", payload)
        self.assertNotIn("fp64", payload)
        self.assertLessEqual(parameters["frames"], 81)

    def test_all_presets_stay_within_frame_and_dtype_contract(self):
        defaults = load_defaults()
        for name, preset in load_presets().items():
            with self.subTest(preset=name):
                options = dict(defaults)
                options.update(preset)
                workflow, parameters = build_wan_workflow(
                    "contract fixture", **options
                )
                payload = json.dumps(workflow, sort_keys=True).lower()
                self.assertNotIn("float64", payload)
                self.assertNotIn("fp64", payload)
                self.assertGreater(parameters["frames"], 0)
                self.assertLessEqual(parameters["frames"], 81)

    def test_precision_fields_are_explicit_and_not_double_precision(self):
        workflow, _ = build_wan_workflow("contract fixture", **load_defaults())
        values = []
        for node in workflow.values():
            inputs = node.get("inputs", {})
            for key in ("precision", "base_precision"):
                if key in inputs:
                    values.append(str(inputs[key]).lower())
        self.assertTrue(values)
        self.assertTrue(set(values) <= {"bf16", "fp16", "float16", "float32"})


if __name__ == "__main__":
    unittest.main()
