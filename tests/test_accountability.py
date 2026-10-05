import tempfile
import unittest
from pathlib import Path

from ia_director.accountability import (
    ArtifactDisposition,
    EnvironmentChange,
    ExecutionLedger,
    classify_path, snapshot_tree,
)


class ExecutionAccountabilityTests(unittest.TestCase):
    def test_ledger_exposes_persistent_footprint_and_artifact_disposition(self):
        ledger = ExecutionLedger("build fixture")
        ledger.record_change(EnvironmentChange("directory", "create", "build", bytes_delta=128))
        ledger.record_change(EnvironmentChange("cache", "create", "cache", persistent=False, bytes_delta=64))
        ledger.record_artifact(ArtifactDisposition("candidate.bin", "reusable", "failed current acceptance only", True))
        ledger.record_test("fixture", "FAIL", "acceptance mismatch")
        record = ledger.as_record()
        self.assertEqual(record["persistent_changes"], 1)
        self.assertEqual(record["known_bytes_delta"], 192)
        self.assertEqual(record["artifacts"][0]["disposition"], "reusable")
        self.assertEqual(record["tests"][0]["status"], "FAIL")

    def test_cleanup_claim_preserves_verification_truth(self):
        ledger = ExecutionLedger("cleanup fixture")
        ledger.record_cleanup("temp-dir", False, "path could not be rechecked")
        record = ledger.as_record()
        self.assertFalse(record["cleanup"][0]["verified"])

    def test_invalid_test_status_fails_closed(self):
        ledger = ExecutionLedger("fixture")
        with self.assertRaises(ValueError):
            ledger.record_test("fixture", "MAYBE", "none")

    def test_path_scope_does_not_require_reading_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(classify_path(root / "artifact.txt", project_root=root), "project")
            self.assertEqual(classify_path(root.parent / "external.txt", project_root=root), "external")


if __name__ == "__main__":
    unittest.main()

class SnapshotNoiseTests(unittest.TestCase):
    def test_snapshot_excludes_vcs_and_python_cache_noise(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.git').mkdir(); (root / '.git' / 'index').write_text('noise')
            (root / '__pycache__').mkdir(); (root / '__pycache__' / 'x.pyc').write_bytes(b'noise')
            (root / 'app.py').write_text('useful')
            snap = snapshot_tree(root)
            self.assertEqual(set(snap), {'app.py'})
