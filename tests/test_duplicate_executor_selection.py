"""Duplicate executor identities must never redirect a verified selection."""
import unittest

from ia_director.selection import CapabilityEvidence, WorkContract, select_capability


def candidate(name, *, risk="low", cost=0.0):
    return CapabilityEvidence(
        name=name, features=frozenset({"software-development"}),
        effects=frozenset({"read", "create", "modify"}),
        destinations=frozenset({"local"}), risk=risk,
        estimated_cost=cost, complexity=1,
        provenance="local:checked", verification="verified",
    )


class DuplicateExecutorSelectionTests(unittest.TestCase):
    def setUp(self):
        self.contract = WorkContract(
            outcome="Develop a local app",
            required_features=frozenset({"software-development"}),
            allowed_effects=frozenset({"read", "create", "modify"}),
            allowed_destinations=frozenset({"local"}),
            max_risk="low", max_cost=0.0,
        )

    def test_unsafe_shadow_cannot_replace_admitted_candidate(self):
        safe = candidate("local.worker")
        unsafe = candidate("local.worker", risk="high")
        chosen, decisions = select_capability(self.contract, (safe, unsafe))
        self.assertIsNone(chosen)
        self.assertEqual(len(decisions), 2)
        self.assertTrue(all(not d.admissible for d in decisions))
        self.assertTrue(all("duplicate capability name" in d.reasons for d in decisions))

    def test_duplicate_safe_names_are_ambiguous_even_if_identical(self):
        chosen, decisions = select_capability(
            self.contract, (candidate("same"), candidate("same")))
        self.assertIsNone(chosen)
        self.assertTrue(all(not d.admissible for d in decisions))

    def test_unique_admissible_fallback_survives_duplicate_poisoning(self):
        fallback = candidate("fallback")
        chosen, decisions = select_capability(
            self.contract,
            (candidate("shared"), candidate("shared", risk="high"), fallback),
        )
        self.assertIs(chosen, fallback)
        self.assertEqual([d.admissible for d in decisions], [False, False, True])

    def test_unique_identity_retains_existing_ranking(self):
        slow = candidate("slow", cost=0.0)
        fast = candidate("fast", cost=0.0)
        chosen, decisions = select_capability(self.contract, (slow, fast))
        self.assertIs(chosen, fast)
        self.assertTrue(all(d.admissible for d in decisions))


if __name__ == "__main__":
    unittest.main()
