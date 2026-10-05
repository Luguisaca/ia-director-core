"""Provider-independent bounded development loop with repair and factual handoff."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from .workspace import WorkspaceExecutionError, run_in_workspace

DevelopmentExecutor=Callable[[Path,str],str]
DevelopmentVerifier=Callable[[Path],tuple[bool,str]]
@dataclass(frozen=True)
class DevelopmentRun:
 status:str
 attempts:int
 verification_evidence:tuple[str,...]
 accountability:dict
 handoff:dict

def run_development(intent:str,workspace:Path,executor:DevelopmentExecutor,verifier:DevelopmentVerifier,*,max_attempts:int=2,context:dict|None=None)->DevelopmentRun:
 """Execute, independently verify, and request bounded repair when verification fails."""
 if not intent.strip():raise ValueError('intent is required')
 if max_attempts<1:raise ValueError('max_attempts must be >= 1')
 evidence:list[str]=[];combined_changes=[];combined_tests=[];last_accountability={}
 instruction=intent.strip()
 for attempt in range(1,max_attempts+1):
  try:run=run_in_workspace(intent,workspace,lambda root:executor(root,instruction),context={**(context or {}),'attempt':attempt,'instruction':instruction})
  except WorkspaceExecutionError as exc:
   last_accountability=exc.accountability;combined_changes.extend(last_accountability.get('changes',[]));combined_tests.extend(last_accountability.get('tests',[]));raise
  last_accountability=run.accountability;combined_changes.extend(last_accountability.get('changes',[]));combined_tests.extend(last_accountability.get('tests',[]))
  passed,detail=verifier(workspace);evidence.append(detail);combined_tests.append({'name':f'independent verification attempt {attempt}','status':'PASS' if passed else 'FAIL','evidence':detail})
  if passed:
   accountability=dict(last_accountability);accountability['changes']=combined_changes;accountability['tests']=combined_tests;accountability['persistent_changes']=len([x for x in combined_changes if x.get('persistent',True)]);accountability['known_bytes_delta']=sum(x.get('bytes_delta') or 0 for x in combined_changes)
   handoff={'status':'HUMAN_TEST_PENDING','objective':intent.strip(),'attempts':attempt,'verification':tuple(evidence),'persistent_changes':accountability['persistent_changes'],'known_bytes_delta':accountability['known_bytes_delta']}
   return DevelopmentRun('HUMAN_TEST_PENDING',attempt,tuple(evidence),accountability,handoff)
  instruction=(f'The previous implementation did not pass independent verification. Original intent: {intent.strip()}\nVerification evidence: {detail}\nInspect the current workspace, repair the implementation, run applicable tests, and leave it ready for independent verification.')
 accountability=dict(last_accountability);accountability['changes']=combined_changes;accountability['tests']=combined_tests
 handoff={'status':'VERIFICATION_FAILED','objective':intent.strip(),'attempts':max_attempts,'verification':tuple(evidence),'persistent_changes':len(combined_changes)}
 return DevelopmentRun('VERIFICATION_FAILED',max_attempts,tuple(evidence),accountability,handoff)
