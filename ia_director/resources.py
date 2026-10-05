"""Owned runtime-resource lifecycle and verified cleanup."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Callable, Literal

Disposition = Literal["CLEANUP", "KEEP"]

@dataclass(frozen=True)
class RuntimeResource:
    kind: str
    identifier: str
    owner: str
    disposition: Disposition = "CLEANUP"
    purpose: str = ""
    close_condition: str = ""

@dataclass(frozen=True)
class CleanupResult:
    resource: RuntimeResource
    action: str
    verified: bool
    evidence: str
    def as_record(self) -> dict:
        return {**asdict(self.resource), "action": self.action, "verified": self.verified, "evidence": self.evidence}

def reconcile_resources(resources: list[RuntimeResource], *, exists: Callable[[RuntimeResource], bool], cleanup: Callable[[RuntimeResource], None]) -> list[CleanupResult]:
    """Fail closed: a run is not clean until each owned resource is absent or explicitly KEEP."""
    results=[]
    for resource in resources:
        if resource.disposition == "KEEP":
            alive=exists(resource)
            results.append(CleanupResult(resource,"kept",alive,"KEEP resource verified alive" if alive else "KEEP resource unexpectedly absent"))
            continue
        if exists(resource): cleanup(resource)
        alive=exists(resource)
        results.append(CleanupResult(resource,"cleanup",not alive,"resource absent after cleanup" if not alive else "resource still present after cleanup"))
    return results

def cleanup_gate(results: list[CleanupResult]) -> None:
    failed=[r for r in results if not r.verified]
    if failed:
        ids=", ".join(r.resource.identifier for r in failed)
        raise RuntimeError(f"cleanup gate failed: {ids}")
