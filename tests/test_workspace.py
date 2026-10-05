import tempfile
import unittest
from pathlib import Path

from ia_director.workspace import WorkspaceExecutionError, run_in_workspace


class WorkspaceRunTests(unittest.TestCase):
    def test_executor_changes_are_observed_without_provider_coupling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def executor(workspace):
                (workspace / "app.py").write_text("print('ok')")
                return "done"
            run = run_in_workspace("create fixture app", root, executor)
            self.assertEqual(run.result, "done")
            self.assertEqual(run.accountability["tests"][0]["status"], "PASS")
            self.assertEqual(run.accountability["changes"][0]["target"], "app.py")

    def test_executor_failure_preserves_accountability_and_partial_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def executor(workspace):
                (workspace / "partial.txt").write_text("valuable partial")
                raise RuntimeError("fixture failure")
            with self.assertRaises(WorkspaceExecutionError) as caught:
                run_in_workspace("failing fixture", root, executor)
            self.assertTrue((root / "partial.txt").exists())
            evidence = caught.exception.accountability
            self.assertEqual(evidence["tests"][0]["status"], "INCONCLUSIVE")
            self.assertEqual(evidence["changes"][0]["target"], "partial.txt")
            self.assertEqual(evidence["changes"][0]["action"], "create")
            self.assertIsInstance(caught.exception.__cause__, RuntimeError)

    def test_workspace_must_preexist(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"
            with self.assertRaises(ValueError):
                run_in_workspace("fixture", missing, lambda _root: "no")


if __name__ == "__main__":
    unittest.main()
