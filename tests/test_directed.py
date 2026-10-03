import json
import sys
import tempfile
import unittest
from pathlib import Path

from ia_director.capabilities import BuiltinProvider, DiscoveredCapability, StaticProvider
from ia_director.directed import DirectedAuthorization, action_digest, reconcile_interrupted_record, run_contract
from ia_director.processes import run_bounded_process
from ia_director.selection import CapabilityEvidence, WorkContract


class DirectedContractTests(unittest.TestCase):
    def contract(self, feature="digest"):
        return WorkContract(
            outcome="produce a locally verified fixture result",
            required_features=frozenset({feature}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
            acceptance_criteria=("verified result exists",),
            max_risk="low",
            max_cost=0.0,
            targets=frozenset({"fixture://local"}),
        )

    def auth(self, *names):
        return DirectedAuthorization(
            granted=True,
            granted_by="human-fixture",
            allowed_capabilities=frozenset(names),
            allowed_targets=frozenset({"fixture://local"}),
        )

    def test_contract_selection_runs_through_policy_verification_and_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            record, path = run_contract(
                self.contract(),
                "  hello   world  ",
                self.auth("builtin.sha256"),
                Path(tmp),
                (BuiltinProvider(),),
            )
            self.assertEqual(record["selection"]["selected"], "builtin.sha256")
            self.assertTrue(record["policy"]["allowed"])
            self.assertTrue(record["verification"]["passed"])
            self.assertEqual(record["status"], "HUMAN_TEST_PENDING")
            self.assertEqual(json.loads(path.read_text())["id"], record["id"])

    def test_sensitive_payload_and_result_are_not_persisted(self):
        secret = "super-secret-fixture-value"
        with tempfile.TemporaryDirectory() as tmp:
            record, path = run_contract(
                self.contract("normalize"),
                secret,
                self.auth("builtin.normalize"),
                Path(tmp),
                (BuiltinProvider(),),
            )
            persisted = path.read_text()
            self.assertEqual(record["status"], "HUMAN_TEST_PENDING")
            self.assertFalse(record["execution"]["result_persisted"])
            self.assertNotIn(secret, persisted)

    def test_selection_does_not_expand_human_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            record, _ = run_contract(
                self.contract(),
                "hello",
                self.auth("builtin.normalize"),
                Path(tmp),
                (BuiltinProvider(),),
            )
            self.assertEqual(record["selection"]["selected"], "builtin.sha256")
            self.assertFalse(record["policy"]["allowed"])
            self.assertEqual(record["status"], "POLICY_BLOCKED")
            self.assertIsNone(record["execution"])

    def test_no_admissible_capability_is_persisted_without_fake_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            record, _ = run_contract(
                self.contract("semantic-summary"),
                "hello",
                self.auth("builtin.sha256", "builtin.normalize"),
                Path(tmp),
                (BuiltinProvider(),),
            )
            self.assertEqual(record["status"], "NO_ADMISSIBLE_CAPABILITY")
            self.assertIsNone(record["selection"]["selected"])
            self.assertIsNone(record["execution"])

    def test_material_risk_requires_exact_action_bound_approval(self):
        contract = WorkContract(
            outcome="synthetic remote read",
            required_features=frozenset({"remote-read"}),
            allowed_effects=frozenset({"read"}),
            allowed_destinations=frozenset({"remote"}),
            acceptance_criteria=("remote status is independently verified",),
            targets=frozenset({"fixture://remote-host"}),
            max_risk="medium",
            max_cost=0.0,
        )
        evidence = CapabilityEvidence(
            name="fixture.remote-read",
            features=frozenset({"remote-read"}),
            effects=frozenset({"read"}),
            destinations=frozenset({"remote"}),
            risk="medium",
            estimated_cost=0.0,
            complexity=2,
            provenance="fixture",
            verification="exact synthetic result",
        )
        provider = StaticProvider(
            [DiscoveredCapability(evidence=evidence, execute=lambda _p: "ok", verify=lambda _p, r: r == "ok")]
        )
        base = dict(
            granted=True,
            granted_by="human-fixture",
            allowed_capabilities=frozenset({"fixture.remote-read"}),
            allowed_targets=frozenset({"fixture://remote-host"}),
            allowed_effects=frozenset({"read"}),
            allowed_destinations=frozenset({"remote"}),
            max_risk="medium",
        )
        with tempfile.TemporaryDirectory() as tmp:
            blocked, _ = run_contract(
                contract, "read status", DirectedAuthorization(**base), Path(tmp), (provider,)
            )
            self.assertEqual(blocked["status"], "POLICY_BLOCKED")
            self.assertIn(
                "material-risk action lacks exact action-bound approval",
                blocked["policy"]["reasons"],
            )

        approval = action_digest("fixture.remote-read", contract.targets, "read status")
        with tempfile.TemporaryDirectory() as tmp:
            allowed, _ = run_contract(
                contract,
                "read status",
                DirectedAuthorization(**base, approval_digest=approval),
                Path(tmp),
                (provider,),
            )
            self.assertEqual(allowed["status"], "HUMAN_TEST_PENDING")
            self.assertTrue(allowed["verification"]["passed"])

    def test_verification_failure_never_reaches_human_test(self):
        evidence = CapabilityEvidence(
            name="fixture.bad-verifier",
            features=frozenset({"digest"}),
            effects=frozenset(),
            destinations=frozenset({"local"}),
            risk="low",
            estimated_cost=0.0,
            complexity=1,
            provenance="fixture",
            verification="independent fixture rejection",
        )
        provider = StaticProvider(
            [DiscoveredCapability(evidence=evidence, execute=lambda _p: "result", verify=lambda _p, _r: False)]
        )
        with tempfile.TemporaryDirectory() as tmp:
            record, _ = run_contract(
                self.contract(),
                "hello",
                self.auth("fixture.bad-verifier"),
                Path(tmp),
                (provider,),
            )
            self.assertEqual(record["status"], "VERIFICATION_FAILED")
            self.assertFalse(record["verification"]["passed"])
            self.assertFalse(record["human_gate"]["reached"])

    def test_incomplete_contract_cannot_select_or_execute(self):
        incomplete = WorkContract(
            outcome="do useful work",
            required_features=frozenset({"digest"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
        )
        with tempfile.TemporaryDirectory() as tmp:
            record, _ = run_contract(
                incomplete,
                "hello",
                self.auth("builtin.sha256"),
                Path(tmp),
                (BuiltinProvider(),),
            )
            self.assertEqual(record["status"], "CONTRACT_INCOMPLETE")
            self.assertIn("execution target is missing", record["contract_issues"])
            self.assertIsNone(record["selection"]["selected"])
            self.assertIsNone(record["execution"])

    def test_benign_external_process_runs_end_to_end_without_human_transport(self):
        evidence = CapabilityEvidence(
            name="fixture.external-process",
            features=frozenset({"digest"}),
            effects=frozenset(),
            destinations=frozenset({"local"}),
            risk="low",
            estimated_cost=0.0,
            complexity=2,
            provenance=sys.executable,
            verification="exact fixture output",
        )

        def execute(_payload):
            result = run_bounded_process(
                [sys.executable, "-c", "print('external-fixture-ok')"],
                timeout_seconds=2,
            )
            if result.timed_out or result.returncode != 0:
                raise RuntimeError("bounded fixture process failed")
            return result.stdout.strip()

        provider = StaticProvider(
            [
                DiscoveredCapability(
                    evidence=evidence,
                    execute=execute,
                    verify=lambda _payload, result: result == "external-fixture-ok",
                )
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            record, _ = run_contract(
                self.contract(),
                "fixture input",
                self.auth("fixture.external-process"),
                Path(tmp),
                (provider,),
            )
            self.assertEqual(record["status"], "HUMAN_TEST_PENDING")
            self.assertTrue(record["verification"]["passed"])
            self.assertFalse(record["execution"]["result_persisted"])

    def test_interrupted_executor_leaves_reconstructable_non_done_record(self):
        evidence = CapabilityEvidence(
            name="fixture.crash",
            features=frozenset({"digest"}),
            effects=frozenset(),
            destinations=frozenset({"local"}),
            risk="low",
            estimated_cost=0.0,
            complexity=1,
            provenance="fixture",
            verification="fixture verifier",
        )

        def crash(_payload):
            raise RuntimeError("fixture interruption")

        provider = StaticProvider(
            [DiscoveredCapability(evidence=evidence, execute=crash, verify=lambda _p, _r: True)]
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(RuntimeError):
                run_contract(
                    self.contract(),
                    "hello",
                    self.auth("fixture.crash"),
                    root,
                    (provider,),
                )
            paths = list(root.glob("*.json"))
            self.assertEqual(len(paths), 1)
            pending = json.loads(paths[0].read_text())
            self.assertEqual(pending["status"], "EXECUTION_PENDING")
            reconciled = reconcile_interrupted_record(paths[0])
            self.assertEqual(reconciled["status"], "INTERRUPTED")
            self.assertNotEqual(reconciled["status"], "HUMAN_TEST_PENDING")

    def test_wrong_target_is_blocked_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth = DirectedAuthorization(
                granted=True,
                granted_by="human-fixture",
                allowed_capabilities=frozenset({"builtin.sha256"}),
                allowed_targets=frozenset({"fixture://other"}),
            )
            record, _ = run_contract(
                self.contract(), "hello", auth, Path(tmp), (BuiltinProvider(),)
            )
            self.assertEqual(record["status"], "POLICY_BLOCKED")
            self.assertIn("contract target is outside authorization", record["policy"]["reasons"])
            self.assertIsNone(record["execution"])

    def test_wrong_target_is_blocked_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth = DirectedAuthorization(
                granted=True,
                granted_by="human-fixture",
                allowed_capabilities=frozenset({"builtin.sha256"}),
                allowed_targets=frozenset({"fixture://other"}),
            )
            record, _ = run_contract(
                self.contract(), "hello", auth, Path(tmp), (BuiltinProvider(),)
            )
            self.assertEqual(record["status"], "POLICY_BLOCKED")
            self.assertIn("contract target is outside authorization", record["policy"]["reasons"])
            self.assertIsNone(record["execution"])

    def test_missing_human_identity_blocks_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth = DirectedAuthorization(
                granted=True,
                granted_by=None,
                allowed_capabilities=frozenset({"builtin.sha256"}),
                allowed_targets=frozenset({"fixture://local"}),
            )
            record, _ = run_contract(
                self.contract(), "hello", auth, Path(tmp), (BuiltinProvider(),)
            )
            self.assertEqual(record["status"], "POLICY_BLOCKED")
            self.assertIsNone(record["execution"])


if __name__ == "__main__":
    unittest.main()
