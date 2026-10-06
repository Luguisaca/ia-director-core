import sys,tempfile,unittest
from pathlib import Path
from ia_director.codex_app_server import execute_turn

class CodexAppServerTests(unittest.TestCase):
 def test_correlates_responses_and_waits_for_terminal_event(self):
  fixture=Path(__file__).parent/'fixtures'/'fake_codex_app_server.py'
  with tempfile.TemporaryDirectory() as tmp:
   result=execute_turn('unused',Path(tmp),'fixture',timeout_seconds=5,command=[sys.executable,str(fixture)])
  self.assertEqual(result.status,'completed')
  self.assertEqual(result.thread_id,'fixture-thread')
  self.assertIn('thread/started',result.event_methods)
  self.assertIn('item/started',result.event_methods)
  self.assertIn('turn/completed',result.event_methods)
  self.assertEqual(result.status,'completed')

if __name__=='__main__':unittest.main()
