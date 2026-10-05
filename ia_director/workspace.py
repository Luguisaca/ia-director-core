"""Provider-independent bounded workspace execution wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from dataclasses import asdict
import uuid

from .accountability import ExecutionLedger, record_tree_delta, snapshot_tree
from .continuity import read_execution_checkpoint, persist_execution_checkpoint
from .core import now_utc


@dataclass(frozen=True)
class WorkspaceRun:
    result: str
    accountability: dict


class WorkspaceExecutionError(RuntimeError):
    """Executor failure that preserves observable workspace accountability."""

    def __init__(self, message: str, *, accountability: dict, checkpoint: dict | None = None) -> None:
        super().__init__(message)
        self.accountability = accountability
        self.checkpoint = checkpoint
        self.status = 'UNKNOWN'


def _snapshot(root: Path) -> dict:
    return {key: value for key, value in snapshot_tree(root).items()
            if not key.startswith('.ia-director/recovery/')}


def run_in_workspace(
    objective: str,
    workspace: Path,
    executor: Callable[[Path], str],
    *, context: dict | None = None,
) -> WorkspaceRun:
    """Observe project-local filesystem effects around an admitted executor."""
    root = workspace.resolve()
    if not root.is_dir():
        raise ValueError("workspace must be an existing directory")
    previous = read_execution_checkpoint(root)
    if previous and previous['status'] != 'COMPLETED':
        decision = (previous.get('reconciliation') or {}).get('decision')
        if previous['status'] != 'RECONCILED' or decision != 'safe-to-retry':
            raise WorkspaceExecutionError('reconciliation required before execution; remains IA work',
                accountability=previous.get('accountability', {}), checkpoint=previous)
    ledger = ExecutionLedger(objective)
    before = _snapshot(root)
    checkpoint = {'id': 'checkpoint', 'operation_id': str(uuid.uuid4()),
        'objective': objective, 'workspace': str(root), 'context': context or {},
        'status': 'IN_FLIGHT', 'created_at': now_utc(),
        'before': {key: asdict(value) for key, value in before.items()},
        'previous_operation': previous['operation_id'] if previous else None,
        'human_gate': {'reached': False, 'reason': None}}
    persist_execution_checkpoint(root, checkpoint)
    try:
        result = executor(root)
        after = _snapshot(root)
        record_tree_delta(ledger, before, after)
    except BaseException as exc:
        try:
            record_tree_delta(ledger, before, _snapshot(root))
        except Exception as observation_error:
            ledger.record_test('workspace observation', 'INCONCLUSIVE', type(observation_error).__name__)
        ledger.record_test("executor completion", "INCONCLUSIVE", f"executor interrupted: {type(exc).__name__}")
        checkpoint['status'] = 'UNKNOWN'
        checkpoint['accountability'] = ledger.as_record()
        persist_execution_checkpoint(root, checkpoint)
        raise WorkspaceExecutionError(
            "workspace execution interrupted; outcome UNKNOWN; reconciliation required",
            accountability=ledger.as_record(),
            checkpoint=checkpoint,
        ) from exc
    ledger.record_test("executor completion", "PASS", "executor returned normally")
    checkpoint['status'] = 'COMPLETED'
    checkpoint['accountability'] = ledger.as_record()
    persist_execution_checkpoint(root, checkpoint)
    return WorkspaceRun(result=result, accountability=ledger.as_record())
