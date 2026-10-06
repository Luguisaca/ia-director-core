import unittest
from unittest.mock import Mock,patch
from ia_director.runtime import AcquisitionPlan,execute_acquisition,plan_development_acquisition

class AcquisitionPlanningTests(unittest.TestCase):
 def test_missing_runtime_with_npm_becomes_explicit_install_authority_gate(self):
  with patch("ia_director.runtime._codex_cli",return_value=None),patch("ia_director.runtime._npm_cli",return_value=r"C:\tools\npm.cmd"):
   plans=plan_development_acquisition()
  self.assertEqual(len(plans),1);self.assertEqual(plans[0].kind,"install")
  self.assertTrue(plans[0].human_authority_required);self.assertIn("@openai/codex",plans[0].action)
 def test_installed_but_unauthenticated_runtime_becomes_authentication_gate(self):
  with patch("ia_director.runtime._codex_cli",return_value=r"C:\tools\codex.cmd"),patch("ia_director.runtime._codex_authenticated",return_value=False):
   plan=plan_development_acquisition()[0]
  self.assertEqual(plan.kind,"authentication");self.assertEqual(plan.action[-1],"login")
 def test_authentication_uses_native_codex_executable_when_wrapper_node_path_is_stale(self):
  with patch("ia_director.runtime._codex_cli",return_value=r"C:\\Profile\\qa\\AppData\\Roaming\\npm\\codex.cmd"),patch("ia_director.runtime._codex_authenticated",return_value=False),patch("ia_director.runtime._codex_executable",return_value=r"C:\\Profile\\qa\\AppData\\Roaming\\npm\\node_modules\\@openai\\codex\\vendor\\codex.exe"):
   plan=plan_development_acquisition()[0]
  self.assertEqual(plan.kind,"authentication");self.assertEqual(plan.action[-1],"login")
  self.assertTrue(plan.action[0].lower().endswith("codex.exe"))
 def test_windows_package_manager_can_acquire_missing_node_prerequisite(self):
  with patch("ia_director.runtime._codex_cli",return_value=None),patch("ia_director.runtime._npm_cli",return_value=None),patch("ia_director.runtime._winget_cli",return_value="winget"):
   plan=plan_development_acquisition()[0]
  self.assertEqual(plan.capability,"environment.tool.npm");self.assertEqual(plan.kind,"install-prerequisite")
  self.assertIn("OpenJS.NodeJS.LTS",plan.action)
 def test_posix_npm_acquisition_uses_user_scope_without_elevation(self):
  with patch("ia_director.runtime._codex_cli",return_value=None),patch("ia_director.runtime._npm_cli",return_value="/usr/bin/npm"),patch("ia_director.runtime.os.name","posix"):
   plan=plan_development_acquisition()[0]
  self.assertEqual(plan.kind,"install");self.assertIn("--prefix",plan.action);self.assertNotIn("-g",plan.action);self.assertTrue(any(".local" in part for part in plan.action))
 def test_authorized_acquisition_executor_reports_result(self):
  plan=AcquisitionPlan("x",("tool","install"),"scope","reason",True,"install")
  with patch("ia_director.runtime.subprocess.run",return_value=Mock(returncode=0)) as run:
   ok,evidence=execute_acquisition(plan)
  self.assertTrue(ok);self.assertEqual(evidence,"acquisition exit=0");run.assert_called_once()
 def test_no_supported_acquisition_transport_does_not_invent_one(self):
  with patch("ia_director.runtime._codex_cli",return_value=None),patch("ia_director.runtime._npm_cli",return_value=None),patch("ia_director.runtime._winget_cli",return_value=None):
   self.assertEqual(plan_development_acquisition(),())
if __name__=="__main__":unittest.main()
