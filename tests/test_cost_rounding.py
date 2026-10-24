"""Exact decimal budget comparison for composed capability evidence."""
import unittest

from ia_director.selection import CapabilityEvidence, WorkContract, select_capability_set


def capability(name, feature, cost):
    return CapabilityEvidence(
        name=name,
        features=frozenset({feature}),
        effects=frozenset(),
        destinations=frozenset({"local"}),
        risk="low",
        estimated_cost=cost,
        complexity=1,
        provenance="test-fixture",
        verification="test-fixture",
    )


def contract(budget):
    return WorkContract(
        outcome="safe composition",
        required_features=frozenset({"a", "b"}),
        allowed_effects=frozenset(),
        allowed_destinations=frozenset({"local"}),
        max_cost=budget,
    )


class CostRoundingRegression(unittest.TestCase):
    def test_small_positive_cost_cannot_disappear_at_budget_boundary(self):
        candidates = (capability("a", "a", 1.0), capability("b", "b", 1e-16))
        chosen, _ = select_capability_set(contract(1.0), candidates)
        self.assertIsNone(chosen, "rounded float sum must not bypass strict budget")

    def test_decimal_exact_sum_is_allowed_at_boundary(self):
        candidates = (capability("a", "a", 0.1), capability("b", "b", 0.2))
        chosen, _ = select_capability_set(contract(0.3), candidates)
        self.assertEqual({item.name for item in chosen or ()}, {"a", "b"})

    def test_large_budget_does_not_erase_small_cost(self):
        candidates = (capability("a", "a", 1e30), capability("b", "b", 1.0))
        chosen, _ = select_capability_set(contract(1e30), candidates)
        self.assertIsNone(chosen)

    def test_tiny_positive_cost_cannot_disappear(self):
        candidates = (capability("a", "a", 1e308), capability("b", "b", 1e-300))
        chosen, _ = select_capability_set(contract(1e308), candidates)
        self.assertIsNone(chosen)

    def test_overflowed_sum_stays_rejected(self):
        candidates = (capability("a", "a", 1e308), capability("b", "b", 1e308))
        chosen, _ = select_capability_set(contract(None), candidates)
        self.assertIsNone(chosen)

    def test_rejects_rounded_budget_bypass_in_unordered_candidates(self):
        candidates = (capability("b", "b", 1e-16), capability("a", "a", 1.0))
        chosen, _ = select_capability_set(contract(1.0), candidates)
        self.assertIsNone(chosen)


if __name__ == "__main__":
    unittest.main()
