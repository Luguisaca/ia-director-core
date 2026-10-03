import json
import tempfile
import unittest
from pathlib import Path

from ia_director.core import Authorization, IntentDigestCapability, policy_gate, run_intent


class CoreWorkflowTests(unittest.TestCase):
    def test_authorized_flow(self):
        with tempfile.TemporaryDirectory() as temporary:
            auth = Authorization(True, "human@example.test", IntentDigestCapability.name, "low")
            record, path = run_intent("  demo:   safe work  ", auth, Path(temporary))
            self.assertEqual(record["status"], "HUMAN_TEST_PENDING")
            self.assertTrue(record["policy"]["allowed"])
            self.assertTrue(record["verification"]["passed"])
            self.assertTrue(record["human_gate"]["reached"])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), record)
            self.assertEqual({x["state"] for x in record["epistemic"]}, {"DECISION","HYPOTHESIS","FINDING","PENDING"})

    def test_missing_authorization_blocks_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            auth = Authorization(False, None, IntentDigestCapability.name, "low")
            record, path = run_intent("demo: safe work", auth, Path(temporary))
            self.assertEqual(record["status"], "POLICY_BLOCKED")
            self.assertIsNone(record["execution"])
            self.assertTrue(path.exists())

    def test_scope_and_risk_are_enforced(self):
        cap = IntentDigestCapability()
        allowed, reasons = policy_gate(cap, Authorization(True, "human", "other", "low"))
        self.assertFalse(allowed)
        self.assertIn("authorization scope does not match the selected capability", reasons)
        allowed, reasons = policy_gate(cap, Authorization(True, "human", cap.name, "medium"))
        self.assertFalse(allowed)
        self.assertIn("authorization risk tier does not match the selected capability", reasons)

    def test_real_intent_without_capability_is_not_faked(self):
        with tempfile.TemporaryDirectory() as temporary:
            auth = Authorization(True, "human", IntentDigestCapability.name, "low")
            record, _ = run_intent("Create a remote support capability", auth, Path(temporary))
            self.assertEqual(record["status"], "NO_CAPABILITY")
            self.assertIsNone(record["execution"])

    def test_blank_intent_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                run_intent("   ", Authorization(True, "human", IntentDigestCapability.name, "low"), Path(temporary))


if __name__ == "__main__":
    unittest.main()
