import unittest

from ia_director.intent import derive_development_contract


class IntentResolutionTests(unittest.TestCase):
    def test_development_intent_gets_transversal_acceptance_without_human_spec_transport(self):
        result = derive_development_contract("Create a small dating application", target="workspace://project")
        self.assertIsNotNone(result.contract)
        self.assertFalse(result.human_decisions_required)
        self.assertIn("requested outcome is functionally demonstrable", result.contract.acceptance_criteria)
        self.assertEqual(result.contract.targets, frozenset({"workspace://project"}))
        self.assertIsNone(result.contract.max_cost)
        self.assertNotIn("zero external service cost", result.inferred)

    def test_explicit_cost_limit_is_preserved(self):
        result = derive_development_contract(
            "Create application", target="workspace://project", max_cost=12.5
        )
        self.assertIsNotNone(result.contract)
        self.assertEqual(result.contract.max_cost, 12.5)

    def test_missing_outcome_is_a_real_human_information_gate(self):
        result = derive_development_contract("   ", target="workspace://project")
        self.assertIsNone(result.contract)
        self.assertIn("desired outcome is missing", result.human_decisions_required)

    def test_missing_authorized_target_is_not_invented(self):
        result = derive_development_contract("Create application", target="")
        self.assertIsNone(result.contract)
        self.assertIn("authorized development target is missing", result.human_decisions_required)


if __name__ == "__main__":
    unittest.main()
