"""Tests for craft_pojia_bridge module."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "craft_pojia_bridge",
    ROOT / "scripts" / "craft_pojia_bridge.py"
)
assert SPEC is not None and SPEC.loader is not None
craft_pojia_bridge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(craft_pojia_bridge)


class CraftBridgeTests(unittest.TestCase):
    def test_find_craft_anything_cli(self):
        cli = craft_pojia_bridge.find_craft_anything_cli()
        # On this environment, craft-anything-cli was deployed to PATH
        self.assertIsNotNone(cli)
        if cli:
            self.assertTrue(Path(cli).exists())

    def test_audit_fusion_environment(self):
        report = craft_pojia_bridge.audit_fusion_environment()
        self.assertIn("timestamp", report)
        self.assertIn("python_interpreter", report)
        self.assertIn("pojia_components", report)
        self.assertIn("craft_anything", report)
        self.assertTrue(report["pojia_components"]["triage_artifact"])
        self.assertTrue(report["pojia_components"]["inspect_cil"])
        self.assertTrue(report["pojia_components"]["diff_verifier"])

    def test_hybrid_triage_sample_exe(self):
        sample = ROOT / "tests" / "fixtures" / "sample.exe"
        if not sample.exists():
            self.skipTest("sample.exe fixture missing")

        res = craft_pojia_bridge.hybrid_triage(sample)
        self.assertIn("pojia_triage", res)
        self.assertIn("fusion_insights", res)
        self.assertGreater(res["target_size_bytes"], 0)

        # Check that .NET insight is detected
        insights = " ".join(res["fusion_insights"])
        self.assertIn(".NET", insights)

    def test_dual_track_verify_success(self):
        # Target script that calculates square
        target_code = "import sys\nfor line in sys.stdin:\n    line = line.strip()\n    if line:\n        print(int(line) ** 2)\n"
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as tmp_target:
            tmp_target.write(target_code)
            tmp_target_path = Path(tmp_target.name)

        # Reconstructed python code
        recon_code = "def transform(x: int) -> int:\n    return x ** 2\n"
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as tmp_recon:
            tmp_recon.write(recon_code)
            tmp_recon_path = Path(tmp_recon.name)

        try:
            report = craft_pojia_bridge.dual_track_verify(
                cmd_template=[sys.executable, str(tmp_target_path)],
                py_reconstructed_file=tmp_recon_path,
                function_name="transform",
                input_mode="stdin",
                corpus_count=10,
            )
            self.assertTrue(report["track_2_recreation_fidelity"]["verifier_passed"])
            self.assertTrue(report["track_2_recreation_fidelity"]["clean_room_certified"])
        finally:
            if tmp_target_path.exists():
                tmp_target_path.unlink()
            if tmp_recon_path.exists():
                tmp_recon_path.unlink()


if __name__ == "__main__":
    unittest.main()
