"""Provider-independent bounded workspace execution wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .accountability import ExecutionLedger, record_tree_delta, snapshot_tree


@dataclass(frozen=True)
class WorkspaceRun:
    result: str
    accountability: dict


def run_in_workspace(
    objective: str,
    workspace: Path,
    executor: Callable[[Path], str],
) -> WorkspaceRun:
    """Observe project-local filesystem effects around an admitted executor."""
    root = workspace.resolve()
    if not root.is_dir():
        raise ValueError("workspace must be an existing directory")
    ledger = ExecutionLedger(objective)
    before = snapshot_tree(root)
    try:
        result = executor(root)
    except Exception:
        after = snapshot_tree(root)
        record_tree_delta(ledger, before, after)
        ledger.record_test("executor completion", "FAIL", "executor raised an exception")
        raise
    after = snapshot_tree(root)
    record_tree_delta(ledger, before, after)
    ledger.record_test("executor completion", "PASS", "executor returned normally")
    return WorkspaceRun(result=result, accountability=ledger.as_record())
