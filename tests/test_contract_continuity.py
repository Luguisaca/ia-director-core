import tempfile,unittest
from pathlib import Path
from ia_director.capabilities import DiscoveredCapability,StaticProvider
from ia_director.development_entry import run_discovered_development_intent
from ia_director.selection import CapabilityEvidence

class ContractContinuityTests(unittest.TestCase):
 def test_authorized_provider_destination_survives_selection_and_execution_gate(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ws=root/"work";ws.mkdir();calls=[]
   evidence=CapabilityEvidence("fixture.provider",frozenset({"software-development"}),frozenset({"read","create","modify","delete-project-artifacts"}),frozenset({"local","provider"}),"low",0.0,1,"fixture","fixture verifier")
   def execute(_instruction):
    calls.append("execute");(ws/"app.txt").write_text("ok");return "done"
   cap=DiscoveredCapability(evidence,execute,lambda _i,_o:(ws/"app.txt").read_text()=="ok")
   record,_=run_discovered_development_intent("Build fixture",workspace=ws,records_dir=root/"records",providers=[StaticProvider([cap])],authorized=True,authorized_by="human",allowed_destinations=frozenset({"local","provider"}))
   self.assertEqual(record["status"],"HUMAN_TEST_PENDING")
   self.assertTrue(record["policy"]["allowed"])
   self.assertEqual(calls,["execute"])
   self.assertEqual(record["contract"]["allowed_destinations"],["local","provider"])
if __name__=="__main__":unittest.main()
