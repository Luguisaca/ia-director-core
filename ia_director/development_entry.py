"""Single bounded entry from human development intent to verified human-test handoff."""
from __future__ import annotations
import uuid
from pathlib import Path
from typing import Iterable
from .capabilities import CapabilityProvider,discover_capabilities
from .core import _persist,now_utc
from .development import DevelopmentExecutor,DevelopmentVerifier,run_development
from .intent import derive_development_contract
from .selection import CapabilityEvidence,evaluate_candidate,select_capability
from .workspace import WorkspaceExecutionError

def _evidence_record(evidence:CapabilityEvidence)->dict:
 return {key:sorted(value) if isinstance(value,frozenset) else value for key,value in vars(evidence).items()}

def run_discovered_development_intent(intent:str,*,workspace:Path,records_dir:Path,providers:Iterable[CapabilityProvider],authorized:bool,authorized_by:str|None,max_attempts:int=2,allowed_destinations:frozenset[str]=frozenset({'local'}))->tuple[dict,Path]:
 """Rank provider evidence, authorize, and try bounded development per candidate.

 Provider callbacks must be bound to the supplied workspace. execute receives
 each development/repair instruction; verify receives that instruction and its
 output and must independently verify the workspace deliverable. Discovery is
 inventory only and must not execute development work.
 """
 resolution=derive_development_contract(intent,target=f'workspace://{workspace.resolve()}',allowed_destinations=allowed_destinations)
 candidates=discover_capabilities(providers) if resolution.contract is not None else ()
 selected,decisions=select_capability(resolution.contract,(item.evidence for item in candidates)) if resolution.contract is not None else (None,())
 selection={'ownership':'Director-selected','selected':_evidence_record(selected) if selected else None,'considered':[{'evidence':_evidence_record(item.evidence),'admissible':decision.admissible,'reasons':list(decision.reasons),'score':decision.score} for item,decision in zip(candidates,decisions)],'why':'Lowest declared cost, then complexity among contract-admissible candidates.' if selected else 'No discovered admissible capability. Further discovery remains IA work.'}
 if selected is None:
  incomplete=resolution.contract is None
  record={'schema_version':1,'id':str(uuid.uuid4()),'created_at':now_utc(),'updated_at':now_utc(),'intent':intent,'contract':vars(resolution.contract) if resolution.contract else None,'capability':None,'selection':selection,'policy':{'allowed':False,'reasons':[]},'development':None,'accountability':None,'status':'CONTRACT_INCOMPLETE' if incomplete else 'NO_ADMISSIBLE_CAPABILITY','human_gate':{'reached':incomplete,'reason':'; '.join(resolution.human_decisions_required) if incomplete else None}}
  if record['contract']:
   record['contract']={key:sorted(value) if isinstance(value,frozenset) else value for key,value in record['contract'].items()}
  return record,_persist(record,records_dir)
 ranked=sorted(((decision.score,item) for item,decision in zip(candidates,decisions) if decision.admissible),key=lambda entry:entry[0])
 selection['ranked']=[item.evidence.name for _score,item in ranked]
 selection['attempts']=[]
 selection['why']='Rank admissible candidates by declared cost, complexity, then name; advance only after bounded verification exhaustion.'
 for _score,chosen in ranked:
  selected=chosen.evidence
  selection['selected']=_evidence_record(selected)
  latest:dict[str,str]={}
  def execute(_workspace:Path,instruction:str)->str:
   latest['instruction']=instruction;latest['output']=chosen.execute(instruction)
   return latest['output']
  def verify(_workspace:Path)->tuple[bool,str]:
   passed=chosen.verify(latest['instruction'],latest['output'])
   return passed,f'{selected.name}: {selected.verification}: {"PASS" if passed else "FAIL"}'
  record,path=run_development_intent(intent,workspace=workspace,records_dir=records_dir,capability=selected,executor=execute,verifier=verify,authorized=authorized,authorized_by=authorized_by,max_attempts=max_attempts,allowed_destinations=allowed_destinations)
  selection['attempts'].append({'capability':selected.name,'record_id':record['id'],'status':record['status'],'policy':record['policy'],'development':record['development'],'accountability':record['accountability']})
  record['selection']=selection
  path=_persist(record,records_dir)
  # Only bounded verification exhaustion permits another implementation path.
  # Policy denial and execution errors must never become fallback triggers.
  if record['status']!='VERIFICATION_FAILED':
   return record,path
 selection['why']='All discovered admissible candidates exhausted bounded machine verification.'
 record['human_gate']={'reached':False,'reason':selection['why']}
 return record,_persist(record,records_dir)

def run_development_intent(intent:str,*,workspace:Path,records_dir:Path,capability:CapabilityEvidence,executor:DevelopmentExecutor,verifier:DevelopmentVerifier,authorized:bool,authorized_by:str|None,max_attempts:int=2,allowed_destinations:frozenset[str]=frozenset({'local'}))->tuple[dict,Path]:
 """Derive contract, admit one evidenced capability, execute/repair/verify, persist handoff."""
 target=f'workspace://{workspace.resolve()}'
 resolution=derive_development_contract(intent,target=target,allowed_destinations=allowed_destinations)
 record={'schema_version':1,'id':str(uuid.uuid4()),'created_at':now_utc(),'updated_at':None,'intent':intent,'contract':None,'capability':capability.name,'policy':{'allowed':False,'reasons':[]},'development':None,'accountability':None,'status':'CREATED','human_gate':{'reached':False,'reason':None}}
 if resolution.contract is None:
  record['status']='CONTRACT_INCOMPLETE';record['human_gate']={'reached':True,'reason':'; '.join(resolution.human_decisions_required)};record['updated_at']=now_utc();return record,_persist(record,records_dir)
 contract=resolution.contract
 record['contract']={'outcome':contract.outcome,'targets':sorted(contract.targets),'allowed_effects':sorted(contract.allowed_effects),'allowed_destinations':sorted(contract.allowed_destinations),'acceptance_criteria':list(contract.acceptance_criteria),'max_risk':contract.max_risk,'max_cost':contract.max_cost}
 decision=evaluate_candidate(contract,capability);reasons=list(decision.reasons)
 if not authorized:reasons.append('explicit authorization was not granted')
 if not authorized_by:reasons.append('authorizing human identity is missing')
 record['policy']={'allowed':not reasons,'reasons':reasons}
 if reasons:
  record['status']='POLICY_BLOCKED';record['human_gate']={'reached':True,'reason':'Development capability or authority does not satisfy the contract.'};record['updated_at']=now_utc();return record,_persist(record,records_dir)
 record['status']='EXECUTION_PENDING';record['updated_at']=now_utc();_persist(record,records_dir)
 try:
  result=run_development(intent,workspace,executor,verifier,max_attempts=max_attempts,context={'record_id':record['id'],'capability':capability.name,'contract':record['contract'],'authorized_by':authorized_by,'policy':record['policy']})
 except WorkspaceExecutionError as exc:
  record['status']='UNKNOWN';record['accountability']=exc.accountability;record['checkpoint']=exc.checkpoint;record['updated_at']=now_utc();record['human_gate']={'reached':False,'reason':'Reconcile observable effects before retry or alternate selection; remains IA work.'};_persist(record,records_dir)
  raise
 record['development']={'attempts':result.attempts,'verification_evidence':list(result.verification_evidence)};record['accountability']=result.accountability;record['status']=result.status
 record['human_gate']={'reached':result.status=='HUMAN_TEST_PENDING','reason':'Machine verification passed; human usefulness testing remains authoritative.' if result.status=='HUMAN_TEST_PENDING' else 'Machine verification did not pass; autonomous work exhausted its bounded attempts.'};record['handoff']=result.handoff;record['updated_at']=now_utc();return record,_persist(record,records_dir)
