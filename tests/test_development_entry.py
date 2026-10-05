import json,tempfile,unittest
from pathlib import Path
from ia_director.development_entry import run_development_intent,run_discovered_development_intent
from ia_director.capabilities import DiscoveredCapability,StaticProvider
from dataclasses import replace
from ia_director.selection import CapabilityEvidence
from ia_director.workspace import WorkspaceExecutionError
class DevelopmentEntryTests(unittest.TestCase):
 def capability(self):
  return CapabilityEvidence('fixture.developer',frozenset({'software-development'}),frozenset({'read','create','modify','delete-project-artifacts'}),frozenset({'local'}),'low',0.0,1,'fixture','independent fixture verifier')
 def test_intent_to_persisted_human_test_handoff(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ws=root/'work';ws.mkdir();records=root/'records'
   def execute(workspace,_instruction):(workspace/'app.txt').write_text('ok');return 'completed'
   record,path=run_development_intent('Build fixture',workspace=ws,records_dir=records,capability=self.capability(),executor=execute,verifier=lambda w:((w/'app.txt').read_text()=='ok','exact app fixture'),authorized=True,authorized_by='human-fixture')
   self.assertEqual(record['status'],'HUMAN_TEST_PENDING');self.assertTrue(record['policy']['allowed']);self.assertEqual(json.loads(path.read_text())['id'],record['id']);self.assertEqual(record['handoff']['attempts'],1)
 def test_policy_blocks_unadmitted_effect_before_executor(self):
  bad=CapabilityEvidence('fixture.bad',frozenset({'software-development'}),frozenset({'network'}),frozenset({'local'}),'low',0.0,1,'fixture','fixture')
  called=False
  def execute(_w,_i):
   nonlocal called;called=True;return 'x'
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ws=root/'work';ws.mkdir();record,_=run_development_intent('Build fixture',workspace=ws,records_dir=root/'records',capability=bad,executor=execute,verifier=lambda _w:(True,'x'),authorized=True,authorized_by='human-fixture')
  self.assertEqual(record['status'],'POLICY_BLOCKED');self.assertFalse(called);self.assertIn('effects exceed contract',record['policy']['reasons'])
 def test_director_selects_and_persists_candidates_without_caller_choice(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ws=root/'work';ws.mkdir();calls=[]
   def execute(instruction):
    calls.append(instruction);(ws/'app.txt').write_text('ok');return 'completed'
   selected=self.capability()
   expensive=replace(selected,name='fixture.expensive',estimated_cost=5)
   rejected=replace(selected,name='fixture.network',effects=frozenset({'network'}))
   def unexpected(_instruction):raise AssertionError('unselected executor called')
   providers=[StaticProvider([DiscoveredCapability(expensive,unexpected,lambda _i,_o:False),DiscoveredCapability(rejected,unexpected,lambda _i,_o:False)]),StaticProvider([DiscoveredCapability(selected,execute,lambda _i,_o:(ws/'app.txt').read_text()=='ok')])]
   record,path=run_discovered_development_intent('Build fixture',workspace=ws,records_dir=root/'records',providers=providers,authorized=True,authorized_by='human-fixture')
   self.assertEqual(record['status'],'HUMAN_TEST_PENDING');self.assertEqual(calls,['Build fixture'])
   persisted=json.loads(path.read_text());self.assertEqual(persisted['selection']['selected']['name'],selected.name)
   self.assertEqual(len(persisted['selection']['considered']),3)
   self.assertEqual(persisted['selection']['considered'][1]['reasons'],['effects exceed contract'])
 def test_selected_capability_requires_authorization_and_identity(self):
  for authorized,identity in [(False,'human-fixture'),(True,None)]:
   with self.subTest(authorized=authorized,identity=identity),tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);ws=root/'work';ws.mkdir();calls=[]
    candidate=DiscoveredCapability(self.capability(),lambda instruction:calls.append(instruction),lambda _i,_o:True)
    fallback=DiscoveredCapability(replace(self.capability(),name='fixture.fallback',estimated_cost=1),lambda instruction:calls.append(instruction),lambda _i,_o:True)
    record,path=run_discovered_development_intent('Build fixture',workspace=ws,records_dir=root/'records',providers=[StaticProvider([fallback,candidate])],authorized=authorized,authorized_by=identity)
    self.assertEqual(record['status'],'POLICY_BLOCKED');self.assertEqual(calls,[])
    self.assertEqual(json.loads(path.read_text())['selection']['selected']['name'],self.capability().name)
    self.assertEqual(len(record['selection']['attempts']),1)
 def test_no_admissible_candidate_remains_ia_work(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);bad=replace(self.capability(),risk='high')
   def unexpected(_instruction):raise AssertionError('inadmissible executor called')
   record,path=run_discovered_development_intent('Build fixture',workspace=root,records_dir=root/'records',providers=[StaticProvider([DiscoveredCapability(bad,unexpected,lambda _i,_o:True)])],authorized=True,authorized_by='human-fixture')
   self.assertEqual(record['status'],'NO_ADMISSIBLE_CAPABILITY');self.assertFalse(record['human_gate']['reached'])
   self.assertIsNone(json.loads(path.read_text())['selection']['selected'])
 def test_verification_exhaustion_automatically_tries_next_admissible_candidate(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ws=root/'work';ws.mkdir();calls=[]
   first=replace(self.capability(),name='fixture.a')
   second=replace(first,name='fixture.b')
   third=replace(first,name='fixture.c',estimated_cost=1)
   bad=replace(first,name='fixture.inadmissible',estimated_cost=-1,risk='high')
   def execute(name,instruction):
    calls.append((name,instruction));(ws/'app.txt').write_text(name);return name
   def unexpected(_instruction):raise AssertionError('unselected executor called')
   candidates=[DiscoveredCapability(third,unexpected,lambda _i,_o:True),DiscoveredCapability(second,lambda i:execute(second.name,i),lambda _i,o:o==second.name),DiscoveredCapability(bad,unexpected,lambda _i,_o:True),DiscoveredCapability(first,lambda i:execute(first.name,i),lambda _i,_o:False)]
   record,path=run_discovered_development_intent('Build fixture',workspace=ws,records_dir=root/'records',providers=[StaticProvider(candidates)],authorized=True,authorized_by='human-fixture',max_attempts=2)
   self.assertEqual([name for name,_ in calls],[first.name,first.name,second.name])
   self.assertIn('previous implementation did not pass',calls[1][1])
   self.assertEqual(calls[2][1],'Build fixture')
   self.assertEqual(record['status'],'HUMAN_TEST_PENDING');self.assertTrue(record['human_gate']['reached'])
   persisted=json.loads(path.read_text());selection=persisted['selection']
   self.assertEqual(selection['ranked'],[first.name,second.name,third.name])
   self.assertEqual(selection['selected']['name'],second.name)
   self.assertEqual([a['status'] for a in selection['attempts']],['VERIFICATION_FAILED','HUMAN_TEST_PENDING'])
   self.assertEqual([a['development']['attempts'] for a in selection['attempts']],[2,1])
   for attempt in selection['attempts']:
    earlier=json.loads((root/'records'/f"{attempt['record_id']}.json").read_text())
    self.assertEqual(earlier['status'],attempt['status'])
 def test_all_admissible_candidates_exhaust_machine_work(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);calls=[]
   candidates=[DiscoveredCapability(replace(self.capability(),name=name),lambda i,n=name:calls.append(n) or 'done',lambda _i,_o:False) for name in ['fixture.b','fixture.a']]
   record,path=run_discovered_development_intent('Build fixture',workspace=root,records_dir=root/'records',providers=[StaticProvider(candidates)],authorized=True,authorized_by='human-fixture',max_attempts=1)
   self.assertEqual(calls,['fixture.a','fixture.b'])
   self.assertEqual(record['status'],'VERIFICATION_FAILED');self.assertFalse(record['human_gate']['reached'])
   self.assertEqual(len(json.loads(path.read_text())['selection']['attempts']),2)
 def test_execution_error_does_not_trigger_fallback(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);calls=[]
   def fail(_instruction):calls.append('first');raise RuntimeError('executor failed')
   first=DiscoveredCapability(self.capability(),fail,lambda _i,_o:False)
   second=DiscoveredCapability(replace(self.capability(),name='fixture.next',estimated_cost=1),lambda i:calls.append('second'),lambda _i,_o:True)
   with self.assertRaises(WorkspaceExecutionError):
    run_discovered_development_intent('Build fixture',workspace=root,records_dir=root/'records',providers=[StaticProvider([first,second])],authorized=True,authorized_by='human-fixture')
   self.assertEqual(calls,['first'])
 def test_detailed_verification_evidence_reaches_repair_instruction(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);instructions=[]
   def execute(instruction):instructions.append(instruction);return 'completed'
   candidate=DiscoveredCapability(self.capability(),execute,lambda _i,_o:(False,'no project artifact exists'))
   record,_=run_discovered_development_intent('Build fixture',workspace=root,records_dir=root/'records',providers=[StaticProvider([candidate])],authorized=True,authorized_by='human-fixture',max_attempts=2)
   self.assertEqual(record['status'],'VERIFICATION_FAILED')
   self.assertIn('no project artifact exists',record['development']['verification_evidence'][0])
   self.assertIn('no project artifact exists',instructions[1])
 def test_discovered_callbacks_reuse_bounded_repair_flow(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);ws=root/'work';ws.mkdir();instructions=[];verified=[]
   def execute(instruction):
    instructions.append(instruction);(ws/'app.txt').write_text(str(len(instructions)));return str(len(instructions))
   def verify(instruction,output):
    verified.append((instruction,output));return (ws/'app.txt').read_text()=='2'
   record,_=run_discovered_development_intent('Build fixture',workspace=ws,records_dir=root/'records',providers=[StaticProvider([DiscoveredCapability(self.capability(),execute,verify)])],authorized=True,authorized_by='human-fixture',max_attempts=2)
   self.assertEqual(record['status'],'HUMAN_TEST_PENDING');self.assertEqual(record['development']['attempts'],2)
   self.assertIn('previous implementation did not pass',instructions[1]);self.assertEqual(verified,[(instructions[0],'1'),(instructions[1],'2')])
if __name__=='__main__':unittest.main()
