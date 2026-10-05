from __future__ import annotations
import argparse,json,getpass
from pathlib import Path
from .core import Authorization,run_intent
from .development_entry import run_discovered_development_intent
from .runtime import execute_acquisition,plan_development_acquisition,runtime_development_providers

def _confirm(prompt:str)->bool:
    try:return input(prompt).strip().lower() in {"y","yes","s","si","sí"}
    except EOFError:return False

def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description="IA Director experimental intent entry.")
    parser.add_argument("intent",help="What you want to achieve")
    parser.add_argument("--workspace",type=Path,default=Path("solution"))
    parser.add_argument("--records-dir",type=Path,default=Path(".ia-director")/"records")
    parser.add_argument("--authorize",action="store_true",help="Authorize project-local changes for this run")
    parser.add_argument("--authorized-by")
    parser.add_argument("--allow-provider-data",action="store_true",help="Allow the selected external provider to receive necessary intent/project context")
    parser.add_argument("--legacy-demo",action="store_true")
    parser.add_argument("--scope");parser.add_argument("--risk-tier")
    args=parser.parse_args(argv)
    if args.legacy_demo:
        record,path=run_intent(args.intent,Authorization(args.authorize,args.authorized_by,args.scope,args.risk_tier),args.records_dir)
        print(json.dumps({"record":str(path),"status":record["status"],"human_gate":record["human_gate"]},indent=2))
        return 0 if record["status"]=="HUMAN_TEST_PENDING" else 2
    authorized=args.authorize or _confirm(f"Authorize IA Director to create/modify project artifacts in {args.workspace.resolve()}? [y/N] ")
    if not authorized:
        print(json.dumps({"status":"AUTHORIZATION_REQUIRED","human_gate":{"reached":True,"reason":"Project-local modification authority is required."}},indent=2));return 3
    identity=args.authorized_by or getpass.getuser()
    args.workspace.mkdir(parents=True,exist_ok=True)
    providers=runtime_development_providers(args.workspace)
    discovered=tuple(cap for provider in providers for cap in provider.discover())
    for _ in range(3):
        if discovered:break
        plans=plan_development_acquisition()
        if not plans:
            print(json.dumps({"status":"NO_SUPPORTED_ACQUISITION_PATH","human_gate":{"reached":False,"reason":"Further capability discovery remains IA work."}},indent=2));return 2
        plan=plans[0]
        if not _confirm(f"IA Director needs authority for {plan.kind} in {plan.persistent_scope}: {plan.reason} Authorize this step? [y/N] "):
            print(json.dumps({"status":"ACQUISITION_AUTHORIZATION_REQUIRED","human_gate":{"reached":True,"reason":plan.reason},"acquisition":{"capability":plan.capability,"kind":plan.kind,"persistent_scope":plan.persistent_scope}},indent=2));return 3
        ok,detail=execute_acquisition(plan)
        if not ok:
            print(json.dumps({"status":"ACQUISITION_FAILED","human_gate":{"reached":False,"reason":"Acquisition failed; remediation remains IA work."},"evidence":detail},indent=2));return 2
        providers=runtime_development_providers(args.workspace)
        discovered=tuple(cap for provider in providers for cap in provider.discover())
    if not discovered:
        print(json.dumps({"status":"ACQUISITION_EXHAUSTED","human_gate":{"reached":False,"reason":"Bounded acquisition attempts did not yield a usable capability; remediation remains IA work."}},indent=2));return 2
    needs_provider=any("provider" in cap.evidence.destinations for cap in discovered)
    allow_provider=args.allow_provider_data
    if needs_provider and not allow_provider:
        allow_provider=_confirm("A discovered development capability requires sending necessary intent/project context to its provider. Authorize for this run? [y/N] ")
    destinations=frozenset({"local","provider"}) if allow_provider else frozenset({"local"})
    record,path=run_discovered_development_intent(args.intent,workspace=args.workspace,records_dir=args.records_dir,providers=providers,authorized=True,authorized_by=identity,allowed_destinations=destinations)
    print(json.dumps({"record":str(path),"status":record["status"],"selected":record.get("capability"),"human_gate":record["human_gate"],"selection":record.get("selection")},indent=2))
    return 0 if record["status"]=="HUMAN_TEST_PENDING" else 2

if __name__=="__main__":raise SystemExit(main())
