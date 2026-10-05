"""Runtime discovery for the clean-PC development entry.

Provider-specific adapters live behind the generic capability boundary. Presence,
characterization and authorization remain separate claims.
"""
from __future__ import annotations
import os, shutil, subprocess, sys
from dataclasses import dataclass
from pathlib import Path
from .capabilities import DiscoveredCapability, StaticProvider
from .codex_app_server import execute_turn
from .selection import CapabilityEvidence

def _codex_cli() -> str | None:
    found=shutil.which("codex.cmd") or shutil.which("codex")
    if found:return found
    candidate=Path.home()/"AppData"/"Roaming"/"npm"/"codex.cmd"
    return str(candidate) if candidate.is_file() else None

def _npm_cli() -> str | None:
    found=shutil.which("npm.cmd") or shutil.which("npm")
    if found:return found
    program_files=Path(os.environ.get("ProgramFiles",r"C:\Program Files"))
    candidate=program_files/"nodejs"/"npm.cmd"
    return str(candidate) if candidate.is_file() else None

def _winget_cli() -> str | None:
    return shutil.which("winget")

def _codex_executable() -> str | None:
    direct = _codex_cli()
    if not direct:
        return None
    path = Path(direct)
    if path.suffix.lower() in {".cmd", ".ps1"} or (path.name == "codex" and path.parent.name == "npm"):
        vendor = path.parent / "node_modules" / "@openai" / "codex" / "node_modules" / "@openai" / "codex-win32-x64" / "vendor" / "x86_64-pc-windows-msvc" / "bin" / "codex.exe"
        if vendor.is_file():
            return str(vendor)
    return direct


@dataclass(frozen=True)
class AcquisitionPlan:
    capability: str
    action: tuple[str,...]
    persistent_scope: str
    reason: str
    human_authority_required: bool
    kind: str

def _cli_action(executable:str,*args:str)->tuple[str,...]:
    return ("cmd","/d","/c",executable,*args) if Path(executable).suffix.lower()==".cmd" else (executable,*args)

def _codex_authenticated()->bool:
    executable=_codex_executable()
    if not executable:return False
    try:
        return subprocess.run(_cli_action(executable,"login","status"),capture_output=True,text=True,timeout=15).returncode==0
    except (OSError,subprocess.TimeoutExpired):
        return False

def plan_development_acquisition() -> tuple[AcquisitionPlan,...]:
    """Return the next bounded acquisition/authority step after discovery is insufficient."""
    cli=_codex_cli()
    if cli and not _codex_authenticated():
        executable=_codex_executable() or cli
        return (AcquisitionPlan("runtime.codex.app-server",_cli_action(executable,"login"),"provider authentication","Codex is installed but provider authentication is not usable.",True,"authentication"),)
    npm=_npm_cli()
    if not cli and npm:
        action=_cli_action(npm,"install","-g","@openai/codex")
        return (AcquisitionPlan("runtime.codex.app-server",action,"user/global toolchain","No supported software-development adapter is currently available; npm can acquire the demonstrated Codex adapter.",True,"install"),)
    winget=_winget_cli()
    if not npm and winget:
        action=(winget,"install","--id","OpenJS.NodeJS.LTS","--exact","--accept-package-agreements","--accept-source-agreements")
        return (AcquisitionPlan("environment.tool.npm",action,"user/system toolchain","A supported development adapter is unavailable and npm is missing; Windows Package Manager can acquire the Node.js LTS prerequisite.",True,"install-prerequisite"),)
    return ()

def execute_acquisition(plan:AcquisitionPlan,*,timeout_seconds:float=300.0)->tuple[bool,str]:
    """Execute only an already-authorized acquisition step; inherit stdio for interactive auth."""
    try:
        run=subprocess.run(plan.action,timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return False,"acquisition timed out"
    except OSError as exc:
        return False,f"acquisition launch failed: {type(exc).__name__}"
    return run.returncode==0,f"acquisition exit={run.returncode}"

def verify_workspace(workspace: Path) -> tuple[bool, str]:
    files=[p for p in workspace.rglob("*") if p.is_file() and ".ia-director" not in p.parts and ".git" not in p.parts]
    if not files:
        return False,"no project artifact exists"
    commands=[]
    if (workspace/"pyproject.toml").is_file() or (workspace/"tests").is_dir():
        commands.append([sys.executable,"-m","unittest","discover","-s","tests","-q"])
    npm=_npm_cli()
    if (workspace/"package.json").is_file() and npm:
        commands.append(["cmd","/d","/c",npm,"test"] if Path(npm).suffix.lower()==".cmd" else [npm,"test"])
    evidence=[f"project artifacts: {len(files)}"]
    for command in commands:
        try:
            run=subprocess.run(command,cwd=workspace,capture_output=True,text=True,timeout=120)
        except (OSError,subprocess.TimeoutExpired) as exc:
            evidence.append(f"{' '.join(command)} verifier-error={type(exc).__name__}")
            return False,"; ".join(evidence)
        evidence.append(f"{' '.join(command)} exit={run.returncode}")
        if run.returncode != 0:
            return False,"; ".join(evidence)
    return True,"; ".join(evidence)

class RuntimeDevelopmentProvider:
    def __init__(self, workspace: Path):
        self.workspace=workspace
    def discover(self):
        executable=_codex_executable()
        if not executable or not _codex_authenticated():
            return ()
        evidence=CapabilityEvidence(
            name="runtime.codex.app-server",
            features=frozenset({"software-development"}),
            effects=frozenset({"read","create","modify","delete-project-artifacts"}),
            destinations=frozenset({"local","provider"}),
            risk="low",estimated_cost=0.0,complexity=2,
            provenance=executable,
            verification="workspace artifacts plus applicable local automated checks",
        )
        def execute(instruction:str)->str:
            result=execute_turn(executable,self.workspace,instruction)
            return result.status
        def verify(_instruction:str,_output:str):
            return verify_workspace(self.workspace)
        return (DiscoveredCapability(evidence,execute,verify),)

def runtime_development_providers(workspace: Path):
    return (RuntimeDevelopmentProvider(workspace),)
