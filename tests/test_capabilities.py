import unittest

from ia_director.capabilities import (
    BuiltinProvider,
    EnvironmentToolProvider,
    DiscoveredCapability,
    StaticProvider,
    discover_capabilities,
    execute_contract,
    execute_contract_adaptive,
    characterize_capability,
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
        self.assertTrue({"environment.tool.python3", "environment.tool.python"} & names)
        self.assertTrue(names <= {
            "environment.tool.python3",
            "environment.tool.python",
            "environment.tool.git",
            "environment.tool.curl",
            "environment.tool.node",
            "environment.tool.rg",
            "environment.tool.codex",
            "environment.tool.ollama",
            "environment.tool.wsl",
        })
        for item in capabilities:
            self.assertEqual(item.evidence.effects, frozenset())
            self.assertEqual(item.evidence.destinations, frozenset({"local"}))

    def test_tool_presence_does_not_claim_tool_functionality(self):
        capabilities = EnvironmentToolProvider().discover()
        python = next(x for x in capabilities if x.evidence.name in {"environment.tool.python3", "environment.tool.python"})
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


class AdaptiveCapabilityStrategyTests(unittest.TestCase):
    def candidate(self, name, *, cost, output, verifies):
        return DiscoveredCapability(
            evidence=CapabilityEvidence(
                name=name,
                features=frozenset({"semantic-work"}),
                effects=frozenset(),
                destinations=frozenset({"local"}),
                risk="low",
                estimated_cost=cost,
                complexity=1,
                provenance="fixture",
                verification="independent fixture verifier",
            ),
            execute=lambda _text: output,
            verify=lambda _text, _result: verifies,
        )

    def test_failed_preferred_candidate_is_rejected_and_next_is_tried_without_human_choice(self):
        preferred = self.candidate("candidate.preferred", cost=0.0, output="bad", verifies=False)
        fallback = self.candidate("candidate.fallback", cost=0.1, output="good", verifies=True)
        contract = WorkContract(
            outcome="semantic fixture",
            required_features=frozenset({"semantic-work"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
        )
        record = execute_contract_adaptive(contract, "intent", [StaticProvider([fallback, preferred])])
        self.assertEqual(record.status, "VERIFIED")
        self.assertEqual(record.selected, "candidate.fallback")
        self.assertEqual(
            tuple((x.capability, x.status) for x in record.attempts),
            (
                ("candidate.preferred", "REJECTED_AFTER_VERIFICATION"),
                ("candidate.fallback", "VERIFIED"),
            ),
        )
        self.assertIsNone(record.handoff["human_action_required"])

    def test_handoff_explains_when_discovery_cannot_satisfy_contract(self):
        wrong = self.candidate("candidate.wrong", cost=0.0, output="x", verifies=True)
        contract = WorkContract(
            outcome="different feature",
            required_features=frozenset({"other-feature"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
        )
        record = execute_contract_adaptive(contract, "intent", [StaticProvider([wrong])])
        self.assertEqual(record.status, "NO_VERIFIED_CAPABILITY")
        self.assertIsNone(record.selected)
        self.assertTrue(record.handoff["rejected"])
        self.assertIn("Acquire, authorize", record.handoff["human_action_required"])


class CapabilityCharacterizationTests(unittest.TestCase):
    def test_presence_is_not_promoted_to_functionality(self):
        tool = next(
            x for x in EnvironmentToolProvider().discover()
            if x.evidence.name in {"environment.tool.python3", "environment.tool.python"}
        )
        record = characterize_capability(
            tool,
            observations=("executable found on PATH",),
            adapter="PATH-presence",
        )
        self.assertEqual(record.status, "PRESENCE_ONLY")
        self.assertEqual(record.proven_features, frozenset())

    def test_characterization_can_only_prove_advertised_features(self):
        tool = next(
            x for x in EnvironmentToolProvider().discover()
            if x.evidence.name in {"environment.tool.python3", "environment.tool.python"}
        )
        record = characterize_capability(
            tool,
            proven_features={"tool-present"},
            observations=("version command completed",),
            adapter="version-probe",
        )
        self.assertEqual(record.status, "CHARACTERIZED")
        with self.assertRaisesRegex(ValueError, "cannot prove unadvertised features"):
            characterize_capability(tool, proven_features={"autonomous-development"})

    def test_adapter_observation_does_not_mutate_underlying_capability_evidence(self):
        tool = next(
            x for x in EnvironmentToolProvider().discover()
            if x.evidence.name in {"environment.tool.python3", "environment.tool.python"}
        )
        record = characterize_capability(
            tool,
            observations=("stdio invocation waited for additional input",),
            adapter="stdio-cli",
        )
        self.assertIn("tool-present", tool.evidence.features)
        self.assertEqual(record.status, "PRESENCE_ONLY")
