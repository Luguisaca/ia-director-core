import unittest

from ia_director.capabilities import (
    BuiltinProvider,
    EnvironmentToolProvider,
    DiscoveredCapability,
    StaticProvider,
    discover_capabilities,
    execute_contract,
)
from ia_director.selection import CapabilityEvidence, WorkContract


class CapabilityRuntimeTests(unittest.TestCase):
    def test_discovers_real_builtin_capabilities_and_executes_selected_one(self):
        contract = WorkContract(
            outcome="digest payload",
            required_features=frozenset({"digest"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
            max_cost=0.0,
        )
        record = execute_contract(contract, "hello", [BuiltinProvider()])
        self.assertEqual(record.selected, "builtin.sha256")
        self.assertEqual(record.status, "VERIFIED")
        self.assertTrue(record.verified)

    def test_contract_selects_different_discovered_builtin(self):
        contract = WorkContract(
            outcome="normalize payload",
            required_features=frozenset({"normalize"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
            max_cost=0.0,
        )
        record = execute_contract(contract, " hello   world ", [BuiltinProvider()])
        self.assertEqual(record.selected, "builtin.normalize")
        self.assertEqual(record.result, "hello world")
        self.assertTrue(record.verified)

    def test_external_candidate_is_rejected_before_execution(self):
        calls = []
        external = DiscoveredCapability(
            evidence=CapabilityEvidence(
                name="fixture.external",
                features=frozenset({"semantic-summary"}),
                effects=frozenset(),
                destinations=frozenset({"external"}),
                risk="low",
                estimated_cost=0.01,
                complexity=1,
                provenance="test-fixture",
                verification="fixture",
            ),
            execute=lambda text: calls.append(text) or "summary",
            verify=lambda text, result: True,
        )
        contract = WorkContract(
            outcome="summarize",
            required_features=frozenset({"semantic-summary"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
        )
        record = execute_contract(contract, "harmless", [StaticProvider([external])])
        self.assertEqual(record.status, "NO_ADMISSIBLE_CAPABILITY")
        self.assertEqual(calls, [])

    def test_verification_failure_is_not_success(self):
        bad = DiscoveredCapability(
            evidence=CapabilityEvidence(
                name="fixture.bad",
                features=frozenset({"normalize"}),
                effects=frozenset(),
                destinations=frozenset({"local"}),
                risk="low",
                estimated_cost=0.0,
                complexity=1,
                provenance="test-fixture",
                verification="independent fixture check",
            ),
            execute=lambda text: "wrong",
            verify=lambda text, result: result == "expected",
        )
        contract = WorkContract(
            outcome="normalize",
            required_features=frozenset({"normalize"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
        )
        record = execute_contract(contract, "input", [StaticProvider([bad])])
        self.assertEqual(record.status, "VERIFICATION_FAILED")
        self.assertFalse(record.verified)

    def test_environment_discovery_is_bounded_and_non_executing(self):
        capabilities = EnvironmentToolProvider().discover()
        names = {item.evidence.name for item in capabilities}
        self.assertIn("environment.tool.python3", names)
        self.assertTrue(names <= {
            "environment.tool.python3",
            "environment.tool.git",
            "environment.tool.curl",
            "environment.tool.node",
            "environment.tool.rg",
        })
        for item in capabilities:
            self.assertEqual(item.evidence.effects, frozenset())
            self.assertEqual(item.evidence.destinations, frozenset({"local"}))

    def test_tool_presence_does_not_claim_tool_functionality(self):
        capabilities = EnvironmentToolProvider().discover()
        python = next(x for x in capabilities if x.evidence.name == "environment.tool.python3")
        self.assertEqual(
            python.evidence.features,
            frozenset({"tool-present", "tool:python3"}),
        )
        self.assertNotIn("semantic-summary", python.evidence.features)

    def test_duplicate_identity_fails_closed(self):
        provider = BuiltinProvider()
        with self.assertRaisesRegex(ValueError, "duplicate capability identity"):
            discover_capabilities([provider, provider])


if __name__ == "__main__":
    unittest.main()
