import unittest

from ia_director.selection import (
    CapabilityEvidence,
    WorkContract,
    evaluate_candidate,
    select_capability,
    select_capability_set,
)


def cap(
    name,
    features,
    *,
    effects=frozenset(),
    destinations=frozenset({"local"}),
    risk="low",
    cost=0.0,
    complexity=1,
    provenance="repo:test-fixture",
    verification="deterministic fixture check",
):
    return CapabilityEvidence(
        name=name,
        features=frozenset(features),
        effects=effects,
        destinations=destinations,
        risk=risk,
        estimated_cost=cost,
        complexity=complexity,
        provenance=provenance,
        verification=verification,
    )


class ContractSelectionTests(unittest.TestCase):
    def test_deterministic_sufficiency_avoids_unnecessary_ai(self):
        contract = WorkContract(
            outcome="exact digest",
            required_features=frozenset({"digest"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
            max_cost=1.0,
        )
        deterministic = cap("deterministic.digest", {"digest"}, complexity=1)
        ai = cap("model.general", {"digest", "semantic"}, cost=0.2, complexity=4)
        selected, decisions = select_capability(contract, [ai, deterministic])
        self.assertEqual(selected.name, "deterministic.digest")
        self.assertTrue(all(x.admissible for x in decisions))

    def test_semantic_requirement_selects_capability_by_evidence_not_brand(self):
        contract = WorkContract(
            outcome="summarize fixture",
            required_features=frozenset({"semantic-summary"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
            max_cost=1.0,
        )
        not_semantic = cap("deterministic.digest", {"digest"})
        semantic = cap("fixture.semantic-engine", {"semantic-summary"}, cost=0.1, complexity=2)
        selected, decisions = select_capability(contract, [not_semantic, semantic])
        self.assertEqual(selected.name, "fixture.semantic-engine")
        rejected = next(x for x in decisions if x.capability == "deterministic.digest")
        self.assertIn("missing required features: semantic-summary", rejected.reasons)

    def test_contract_constraint_changes_admissibility(self):
        local_contract = WorkContract(
            outcome="summarize fixture",
            required_features=frozenset({"semantic-summary"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
        )
        external_contract = WorkContract(
            outcome="summarize fixture",
            required_features=frozenset({"semantic-summary"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local", "external"}),
        )
        external = cap(
            "external.semantic",
            {"semantic-summary"},
            destinations=frozenset({"external"}),
            complexity=1,
        )
        self.assertFalse(evaluate_candidate(local_contract, external).admissible)
        self.assertTrue(evaluate_candidate(external_contract, external).admissible)

    def test_missing_safety_evidence_is_not_permission(self):
        contract = WorkContract(
            outcome="safe fixture",
            required_features=frozenset({"semantic-summary"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
        )
        incomplete = cap(
            "unknown.semantic",
            {"semantic-summary"},
            effects=None,
            destinations=None,
            risk=None,
            provenance=None,
            verification=None,
        )
        decision = evaluate_candidate(contract, incomplete)
        self.assertFalse(decision.admissible)
        self.assertIn("effects evidence is missing", decision.reasons)
        self.assertIn("data destination evidence is missing", decision.reasons)
        self.assertIn("provenance evidence is missing", decision.reasons)

    def test_no_admissible_candidate_is_explicit(self):
        contract = WorkContract(
            outcome="semantic",
            required_features=frozenset({"semantic-summary"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
        )
        selected, decisions = select_capability(
            contract, [cap("digest", {"digest"})]
        )
        self.assertIsNone(selected)
        self.assertEqual(len(decisions), 1)
        self.assertFalse(decisions[0].admissible)

    def test_cost_constraint_rejects_otherwise_capable_candidate(self):
        contract = WorkContract(
            outcome="semantic",
            required_features=frozenset({"semantic-summary"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
            max_cost=0.05,
        )
        expensive = cap("semantic", {"semantic-summary"}, cost=0.2)
        decision = evaluate_candidate(contract, expensive)
        self.assertFalse(decision.admissible)
        self.assertIn("cost exceeds contract", decision.reasons)


    def test_composition_covers_contract_when_single_candidate_cannot(self):
        contract = WorkContract(
            outcome="normalize then digest",
            required_features=frozenset({"normalize", "digest"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
            max_cost=0.0,
        )
        normalize = cap("normalize", {"normalize"}, cost=0.0)
        digest = cap("digest", {"digest"}, cost=0.0)
        selected, rejected = select_capability_set(contract, [normalize, digest])
        self.assertEqual({item.name for item in selected or ()}, {"normalize", "digest"})
        self.assertEqual(rejected, ())

    def test_composition_never_uses_constraint_violating_member(self):
        contract = WorkContract(
            outcome="local composite",
            required_features=frozenset({"normalize", "semantic-summary"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
        )
        normalize = cap("normalize", {"normalize"})
        external = cap("external", {"semantic-summary"}, destinations=frozenset({"external"}))
        selected, rejected = select_capability_set(contract, [normalize, external])
        self.assertIsNone(selected)
        self.assertTrue(any("external:" in reason for reason in rejected))

    def test_composition_respects_aggregate_cost(self):
        contract = WorkContract(
            outcome="two features",
            required_features=frozenset({"a", "b"}),
            allowed_effects=frozenset(),
            allowed_destinations=frozenset({"local"}),
            max_cost=0.05,
        )
        a = cap("a", {"a"}, cost=0.03)
        b = cap("b", {"b"}, cost=0.03)
        selected, _ = select_capability_set(contract, [a, b])
        self.assertIsNone(selected)


if __name__ == "__main__":
    unittest.main()
