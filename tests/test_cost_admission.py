"""Regression tests for bounded capability cost admission (stdlib only)."""
import unittest
from ia_director.selection import CapabilityEvidence, WorkContract, contract_issues, evaluate_candidate, select_capability_set


def contract(budget=0.5, features=("digest",)):
    return WorkContract("bounded fixture", frozenset(features), frozenset(), frozenset({"local"}), max_cost=budget)


def evidence(name="fixture.digest", features=("digest",), cost=0.0):
    return CapabilityEvidence(name, frozenset(features), frozenset(), frozenset({"local"}), "low", cost, 1, "repo:test", "fixture")


class CostAdmissionRegression(unittest.TestCase):
    def test_bad_cost_is_never_admissible(self):
        for value in (float('nan'), float('inf'), float('-inf'), -0.01, 'free', True, 10**1000):
            with self.subTest(value=repr(value)):
                self.assertIn('cost evidence is invalid', evaluate_candidate(contract(), evidence(cost=value)).reasons)
                chosen, reasons = select_capability_set(contract(), (evidence(cost=value),))
                self.assertIsNone(chosen)
                self.assertTrue(any('cost evidence is invalid' in reason for reason in reasons))

    def test_bad_budget_is_never_admissible(self):
        for value in (float('nan'), float('inf'), float('-inf'), -0.01, 'free', True, 10**1000):
            with self.subTest(value=repr(value)):
                self.assertIn('cost limit is invalid', evaluate_candidate(contract(value), evidence()).reasons)
                self.assertIn('maximum cost must be finite and nonnegative', contract_issues(contract(value)))
                chosen, reasons = select_capability_set(contract(value), (evidence(),))
                self.assertIsNone(chosen)
                self.assertIn('cost limit is invalid', reasons)

    def test_overflowed_composition_is_rejected_with_and_without_budget(self):
        a=evidence('a', ('a',), 1e308)
        b=evidence('b', ('b',), 1e308)
        for budget in (None, 1e308):
            with self.subTest(budget=budget):
                chosen, _ = select_capability_set(contract(budget, ('a','b')), (a,b))
                self.assertIsNone(chosen)

    def test_valid_zero_and_bounded_costs(self):
        self.assertTrue(evaluate_candidate(contract(0), evidence(cost=0)).admissible)
        self.assertTrue(evaluate_candidate(contract(0.5), evidence(cost=0.25)).admissible)
        self.assertIn('cost exceeds contract', evaluate_candidate(contract(0.1), evidence(cost=0.25)).reasons)
        chosen, _ = select_capability_set(contract(0.5), (evidence(cost=0.25),))
        self.assertIsNotNone(chosen)

    def test_finite_composition_is_admissible(self):
        a=evidence('a', ('a',), 0.1)
        b=evidence('b', ('b',), 0.1)
        chosen, _=select_capability_set(contract(0.3, ('a','b')), (a,b))
        self.assertEqual({x.name for x in chosen or ()}, {'a','b'})

    def test_missing_cost_requires_evidence_if_budget_exists(self):
        self.assertIn('cost evidence is missing', evaluate_candidate(contract(), evidence(cost=None)).reasons)
        chosen, _=select_capability_set(contract(), (evidence(cost=None),))
        self.assertIsNone(chosen)


if __name__=='__main__':
    unittest.main()
