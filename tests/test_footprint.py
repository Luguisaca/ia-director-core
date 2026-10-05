import tempfile
import unittest
from pathlib import Path

from ia_director.accountability import (
    ArtifactDisposition,
    ExecutionLedger,
    human_handoff,
    record_tree_delta,
    snapshot_tree,
)


class FootprintTests(unittest.TestCase):
    def test_tree_delta_captures_create_modify_delete_without_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            existing = root / "existing.txt"
            removed = root / "removed.txt"
            existing.write_text("old")
            removed.write_text("gone")
            before = snapshot_tree(root)
            existing.write_text("new-longer")
            removed.unlink()
            (root / "created.txt").write_text("created")
            after = snapshot_tree(root)
            ledger = ExecutionLedger("tree delta")
            record_tree_delta(ledger, before, after)
            actions = {(x.action, x.target) for x in ledger.changes}
            self.assertEqual(actions, {("modify", "existing.txt"), ("delete", "removed.txt"), ("create", "created.txt")})

    def test_handoff_surfaces_failures_reusable_artifacts_and_cleanup_limits(self):
        ledger = ExecutionLedger("fixture")
        ledger.record_test("build", "FAIL", "exit 1")
        ledger.record_artifact(ArtifactDisposition("candidate", "reusable", "partial value", True))
        ledger.record_cleanup("cache", False, "not rechecked")
        handoff = human_handoff({
            "status": "VERIFICATION_FAILED",
            "accountability": ledger.as_record(),
            "human_gate": {"reached": False},
        })
        self.assertEqual(handoff["status"], "VERIFICATION_FAILED")
        self.assertEqual(len(handoff["failed_or_inconclusive_tests"]), 1)
        self.assertEqual(len(handoff["reusable_artifacts"]), 1)
        self.assertEqual(len(handoff["unverified_cleanup"]), 1)


if __name__ == "__main__":
    unittest.main()
