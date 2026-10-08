"""Progressive resolution of material product decisions."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DecisionCandidate:
    key: str
    question: str
    options: tuple[str, ...]
    recommended: str | None
    evidence: str | None
    inferable: bool
    human_authority_required: bool

@dataclass(frozen=True)
class DecisionResolution:
    resolved: tuple[DecisionCandidate, ...]
    ia_work_required: tuple[str, ...]
    human_decisions_required: tuple[str, ...]

def resolve_material_decisions(candidates):
    resolved=[]; ia_work=[]; human=[]
    for item in candidates:
        if not item.recommended or not item.evidence or item.recommended not in item.options:
            ia_work.append(item.key); continue
        if item.human_authority_required and not item.inferable:
            human.append(f"{item.question} Options: {', '.join(item.options)}. Recommendation: {item.recommended}. Why: {item.evidence}")
            continue
        resolved.append(item)
    return DecisionResolution(tuple(resolved),tuple(ia_work),tuple(human))
