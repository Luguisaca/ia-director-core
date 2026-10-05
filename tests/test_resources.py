import unittest
from ia_director.resources import RuntimeResource, reconcile_resources, cleanup_gate

class RuntimeResourceTests(unittest.TestCase):
    def test_cleanup_removes_owned_resource_and_verifies_absence(self):
        alive={"child"}
        r=RuntimeResource("process","child","run-1")
        out=reconcile_resources([r],exists=lambda x:x.identifier in alive,cleanup=lambda x:alive.discard(x.identifier))
        self.assertTrue(out[0].verified); cleanup_gate(out)

    def test_parent_cleanup_does_not_hide_surviving_child_regression(self):
        # Regression for Windows observation: parent can disappear while child remains.
        alive={"child"}
        child=RuntimeResource("process","child","run-1")
        out=reconcile_resources([child],exists=lambda x:x.identifier in alive,cleanup=lambda x:None)
        self.assertFalse(out[0].verified)
        with self.assertRaises(RuntimeError): cleanup_gate(out)

    def test_keep_requires_explicit_purpose_and_live_verification(self):
        r=RuntimeResource("port","8041","run-1","KEEP","HUMAN QA","close after HUMAN QA")
        out=reconcile_resources([r],exists=lambda x:True,cleanup=lambda x:None)
        self.assertTrue(out[0].verified); self.assertEqual(out[0].action,"kept")

    def test_missing_keep_fails_gate(self):
        r=RuntimeResource("service","qa","run-1","KEEP","HUMAN QA","close after QA")
        out=reconcile_resources([r],exists=lambda x:False,cleanup=lambda x:None)
        with self.assertRaises(RuntimeError): cleanup_gate(out)

if __name__=="__main__": unittest.main()
