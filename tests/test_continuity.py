import unittest

from ia_director.continuity import WorkDisposition, WorkReference, continuity_gate


class ContinuityGateTests(unittest.TestCase):
    def test_validated_experiment_cannot_silently_disappear(self):
        discovered = [
            WorkReference(
                "surface-recon-web-ui",
                "git-branch",
                "experiment/lab-001-rerun-v2",
                "HUMAN QA: loopback UI HTTP/API PASS",
            )
        ]
        with self.assertRaisesRegex(RuntimeError, "missing disposition"):
            continuity_gate(discovered, [])

    def test_integrated_work_requires_current_ref_and_evidence(self):
        item = WorkReference("ui", "prototype", "experiment/ui", "validated")
        with self.assertRaisesRegex(RuntimeError, "insufficient evidence"):
            continuity_gate([item], [WorkDisposition("ui", "integrated", "ported and tested")])

    def test_reconciled_work_passes_with_explicit_disposition(self):
        item = WorkReference("ui", "prototype", "experiment/ui", "validated")
        result = continuity_gate(
            [item],
            [WorkDisposition("ui", "integrated", "regression + CI evidence", "main:surface-recon serve")],
        )
        self.assertEqual(result[0].disposition, "integrated")

    def test_retained_experiment_is_not_forced_into_main(self):
        item = WorkReference("research", "git-branch", "research/hypothesis", "useful negative evidence")
        result = continuity_gate(
            [item],
            [WorkDisposition("research", "retained-experimental", "not product-approved; keep for evidence")],
        )
        self.assertEqual(result[0].disposition, "retained-experimental")


if __name__ == "__main__":
    unittest.main()
