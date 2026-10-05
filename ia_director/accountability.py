"""Structured operational accountability for directed work."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

Disposition = Literal["temporary", "evidence", "reusable", "deliverable", "secure-delete"]


@dataclass(frozen=True)
class EnvironmentChange:
    kind: str
    action: str
    target: str
    scope: str = "project"
    persistent: bool = True
    bytes_delta: int | None = None


@dataclass(frozen=True)
class ArtifactDisposition:
    path: str
    disposition: Disposition
    reason: str
    retained: bool

@dataclass
class ExecutionLedger:
    objective: str
    changes: list[EnvironmentChange] = field(default_factory=list)
    artifacts: list[ArtifactDisposition] = field(default_factory=list)
    tests: list[dict] = field(default_factory=list)
    cleanup: list[dict] = field(default_factory=list)

    def record_change(self, change: EnvironmentChange) -> None:
        self.changes.append(change)

    def record_artifact(self, artifact: ArtifactDisposition) -> None:
        self.artifacts.append(artifact)

    def record_test(self, name: str, status: str, evidence: str) -> None:
        if status not in {"PASS", "FAIL", "INCONCLUSIVE"}:
            raise ValueError("invalid test status")
        self.tests.append({"name": name, "status": status, "evidence": evidence})

    def record_cleanup(self, target: str, verified: bool, evidence: str) -> None:
        self.cleanup.append({"target": target, "verified": verified, "evidence": evidence})

    def as_record(self) -> dict:
        return {
            "objective": self.objective,
            "changes": [asdict(item) for item in self.changes],
            "artifacts": [asdict(item) for item in self.artifacts],
            "tests": list(self.tests),
            "cleanup": list(self.cleanup),
            "persistent_changes": sum(1 for item in self.changes if item.persistent),
            "known_bytes_delta": sum(item.bytes_delta or 0 for item in self.changes),
        }


def classify_path(path: Path, *, project_root: Path) -> str:
    """Return a non-secret scope label without reading file contents."""
    resolved = path.resolve()
    root = project_root.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return "external"
    return "project"

@dataclass(frozen=True)
class FileState:
    size: int
    mtime_ns: int


def snapshot_tree(root: Path) -> dict[str, FileState]:
    """Inventory regular files without reading their contents."""
    if not root.exists():
        return {}
    snapshot: dict[str, FileState] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in {".git", "__pycache__"} for part in relative.parts):
            continue
        if path.is_file() and not path.is_symlink():
            stat = path.stat()
            snapshot[relative.as_posix()] = FileState(stat.st_size, stat.st_mtime_ns)
    return snapshot


def record_tree_delta(
    ledger: ExecutionLedger,
    before: dict[str, FileState],
    after: dict[str, FileState],
) -> None:
    """Record observable project-tree mutations without persisting file contents."""
    for target in sorted(before.keys() | after.keys()):
        old, new = before.get(target), after.get(target)
        if old is None and new is not None:
            ledger.record_change(EnvironmentChange("file", "create", target, bytes_delta=new.size))
        elif old is not None and new is None:
            ledger.record_change(EnvironmentChange("file", "delete", target, bytes_delta=-old.size))
        elif old != new:
            ledger.record_change(EnvironmentChange("file", "modify", target, bytes_delta=new.size - old.size))


def human_handoff(record: dict) -> dict:
    """Create a compact factual handoff from persisted evidence."""
    accountability = record.get("accountability") or {}
    failed = [item for item in accountability.get("tests", []) if item.get("status") != "PASS"]
    reusable = [item for item in accountability.get("artifacts", []) if item.get("disposition") == "reusable"]
    unverified_cleanup = [item for item in accountability.get("cleanup", []) if not item.get("verified")]
    return {
        "status": record.get("status"),
        "objective": accountability.get("objective"),
        "persistent_changes": accountability.get("persistent_changes", 0),
        "known_bytes_delta": accountability.get("known_bytes_delta", 0),
        "failed_or_inconclusive_tests": failed,
        "reusable_artifacts": reusable,
        "unverified_cleanup": unverified_cleanup,
        "human_gate": record.get("human_gate"),
    }
