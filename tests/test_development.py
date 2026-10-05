import tempfile,unittest
from pathlib import Path
from ia_director.development import run_development
class DevelopmentLoopTests(unittest.TestCase):
 def test_repairs_failed_verification_then_reaches_human_test(self):
  calls=[]
  def executor(root,instruction):
   calls.append(instruction)
   (root/'app.txt').write_text('bad' if len(calls)==1 else 'good')
   return 'completed'
  def verifier(root):
   value=(root/'app.txt').read_text();return value=='good',f'app={value}'
  with tempfile.TemporaryDirectory() as tmp:r=run_development('build fixture',Path(tmp),executor,verifier,max_attempts=2)
  self.assertEqual(r.status,'HUMAN_TEST_PENDING');self.assertEqual(r.attempts,2);self.assertEqual(r.verification_evidence,('app=bad','app=good'));self.assertIn('Verification evidence: app=bad',calls[1]);self.assertEqual(r.handoff['status'],'HUMAN_TEST_PENDING')
 def test_stops_after_bounded_failed_repairs(self):
  def executor(root,_instruction):(root/'app.txt').write_text('bad');return 'completed'
  with tempfile.TemporaryDirectory() as tmp:r=run_development('build fixture',Path(tmp),executor,lambda _root:(False,'still bad'),max_attempts=2)
  self.assertEqual(r.status,'VERIFICATION_FAILED');self.assertEqual(r.attempts,2);self.assertEqual(len(r.verification_evidence),2)
if __name__=='__main__':unittest.main()
