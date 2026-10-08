import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ia_director.__main__ import main
from ia_director.capabilities import DiscoveredCapability, StaticProvider
from ia_director.selection import CapabilityEvidence


class DirectorCliEndToEndTests(unittest.TestCase):
    def provider(self, workspace):
        evidence = CapabilityEvidence(
            "fixture.developer",
            frozenset({"software-development"}),
            frozenset({"read", "create", "modify", "delete-project-artifacts"}),
            frozenset({"local"}),
            "low", 0.0, 1, "fixture", "fixture verification",
        )
        def execute(instruction):
            (workspace / "app.txt").write_text("functional:" + instruction, encoding="utf-8")
            return "completed"
        def verify(_instruction, _output):
            artifact = workspace / "app.txt"
            return artifact.is_file() and artifact.read_text(encoding="utf-8").startswith("functional:")
        return (StaticProvider((DiscoveredCapability(evidence, execute, verify),)),)

    def test_intent_reaches_verified_handoff_through_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); workspace = root / "solution"; records = root / "records"
            out = io.StringIO()
            with patch("ia_director.__main__.runtime_development_providers", side_effect=self.provider), redirect_stdout(out):
                code = main(["Create a minimal task application", "--workspace", str(workspace),
                             "--records-dir", str(records), "--authorize", "--authorized-by", "human-fixture"])
            result = json.loads(out.getvalue())
            self.assertEqual(code, 0)
            self.assertEqual(result["status"], "HUMAN_TEST_PENDING")
            self.assertEqual(result["selected"], "fixture.developer")
            self.assertTrue((workspace / "app.txt").is_file())
            persisted = json.loads(Path(result["record"]).read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "HUMAN_TEST_PENDING")

    def test_no_capability_path_leaves_no_workspace_residue(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "solution"
            out = io.StringIO()
            empty = StaticProvider(())
            with patch("ia_director.__main__.runtime_development_providers", return_value=(empty,)), \
                 patch("ia_director.__main__.plan_development_acquisition", return_value=()), \
                 redirect_stdout(out):
                code = main(["Build something", "--workspace", str(workspace),
                             "--authorize", "--authorized-by", "human-fixture"])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(out.getvalue())["status"], "NO_SUPPORTED_ACQUISITION_PATH")
            self.assertFalse(workspace.exists())


if __name__ == "__main__":
    unittest.main()
