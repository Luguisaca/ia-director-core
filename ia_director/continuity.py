"""Fail-closed continuity control for persistent project work.

The control is provider/tool independent: discovery supplies persistent work
references (branches, experiments, prototypes, artifacts, external records);
the gate requires an explicit evidence-backed disposition for every reference
before a project state may be called reconciled.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal
from pathlib import Path
import json
from .core import _persist, now_utc


def execution_checkpoint(workspace: Path) -> Path:
    return workspace.resolve() / '.ia-director' / 'recovery' / 'checkpoint.json'


def read_execution_checkpoint(workspace: Path) -> dict | None:
    path = execution_checkpoint(workspace)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def persist_execution_checkpoint(workspace: Path, record: dict) -> Path:
    record['updated_at'] = now_utc()
    _persist({**record, 'id': record['operation_id']}, execution_checkpoint(workspace).parent)
    return _persist(record, execution_checkpoint(workspace).parent)


@dataclass(frozen=True)
class ReconciliationEvidence:
    """Operation-bound observations supplied by an independent inspector.

    stopped must establish that the executor can no longer apply effects.
    no_effects must cover the entire admitted effect scope, not just file stats.
    verified must independently establish the intended outcome in that scope.
    """
    operation_id: str
    observations: tuple[str, ...]
    stopped: bool = False
    no_effects: bool = False
    verified: bool = False
    rollback_required: bool = False


def reconcile_execution(workspace: Path, evidence: ReconciliationEvidence) -> dict:
    """Record a decision; never execute, retry, roll back, or request authority."""
    record = read_execution_checkpoint(workspace)
    if record is None or record['operation_id'] != evidence.operation_id:
        raise ValueError('evidence does not identify the checkpoint operation')
    if record['status'] not in {'IN_FLIGHT', 'UNKNOWN', 'RECONCILED'}:
        raise ValueError('operation does not require reconciliation')
    decision = 'unresolved'
    supported = bool(evidence.observations) and all(x.strip() for x in evidence.observations)
    conflicting = evidence.no_effects and (evidence.verified or evidence.rollback_required)
    if supported and evidence.stopped and not conflicting:
        if evidence.rollback_required:
            decision = 'rollback-required'
        elif evidence.verified:
            decision = 'already-applied/verified'
        elif evidence.no_effects:
            decision = 'safe-to-retry'
    entry = {'decision': decision, 'evidence': vars(evidence), 'at': now_utc()}
    record.setdefault('reconciliations', []).append(entry)
    record['reconciliation'] = entry
    record['status'] = 'UNKNOWN' if decision == 'unresolved' else 'RECONCILED'
    record['human_gate'] = {'reached': False, 'reason': None}
    persist_execution_checkpoint(workspace, record)
    return record

Disposition = Literal["integrated", "superseded", "rejected", "retained-experimental"]

@dataclass(frozen=True)
class WorkReference:
    identity: str
    kind: str
    source_ref: str
    evidence: str = ""

@dataclass(frozen=True)
class WorkDisposition:
    identity: str
    disposition: Disposition
    evidence: str
    current_ref: str | None = None

def continuity_gate(
    discovered: Iterable[WorkReference],
    dispositions: Iterable[WorkDisposition],
) -> tuple[WorkDisposition, ...]:
    """Require one justified disposition for every discovered persistent work item."""
    items = tuple(discovered)
    records = tuple(dispositions)
    by_id: dict[str, WorkDisposition] = {}
    duplicates: list[str] = []
    for record in records:
        if record.identity in by_id:
            duplicates.append(record.identity)
        by_id[record.identity] = record

    missing = sorted({item.identity for item in items if item.identity not in by_id})
    unexplained = sorted(
        record.identity for record in records
        if not record.evidence.strip()
        or (record.disposition in {"integrated", "superseded"} and not (record.current_ref or "").strip())
    )
    unknown = sorted({record.identity for record in records} - {item.identity for item in items})
    if missing or duplicates or unexplained or unknown:
        detail = []
        if missing: detail.append("missing disposition: " + ", ".join(missing))
        if duplicates: detail.append("duplicate disposition: " + ", ".join(sorted(set(duplicates))))
        if unexplained: detail.append("insufficient evidence/current ref: " + ", ".join(unexplained))
        if unknown: detail.append("disposition without discovered work: " + ", ".join(unknown))
        raise RuntimeError("continuity gate failed: " + "; ".join(detail))
    return tuple(by_id[item.identity] for item in items)
