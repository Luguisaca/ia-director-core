"""Local, deterministic IA Director Core workflow."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class Capability(Protocol):
    """Provider-neutral capability contract."""

    name: str
    risk: str

    def supports(self, intent: str) -> bool: ...
    def execute(self, intent: str) -> dict[str, Any]: ...
    def verify(self, intent: str, result: dict[str, Any]) -> tuple[bool, str]: ...


class IntentDigestCapability:
    """Safe built-in demonstration with no effect outside its work record."""

    name = "builtin.intent_digest"
    risk = "low"

    def supports(self, intent: str) -> bool:
        return intent.strip().lower().startswith("demo:")

    def execute(self, intent: str) -> dict[str, Any]:
        normalized = " ".join(intent.split())
        return {
            "normalized_intent": normalized,
            "sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "character_count": len(normalized),
        }

    def verify(self, intent: str, result: dict[str, Any]) -> tuple[bool, str]:
        passed = result == self.execute(intent)
        return passed, "result matches deterministic recomputation" if passed else "result mismatch"


@dataclass(frozen=True)
class Authorization:
    granted: bool
    granted_by: str | None
    scope: str | None
    risk_tier: str | None


def select_capability(intent: str, capabilities: tuple[Capability, ...]) -> Capability | None:
    return next((item for item in capabilities if item.supports(intent)), None)


def policy_gate(capability: Capability, authorization: Authorization) -> tuple[bool, list[str]]:
    """Allow only explicitly authorized, exactly scoped, low-risk work."""
    reasons: list[str] = []
    if not authorization.granted:
        reasons.append("explicit authorization was not granted")
    if not authorization.granted_by:
        reasons.append("authorizing human identity is missing")
    if authorization.scope != capability.name:
        reasons.append("authorization scope does not match the selected capability")
    if authorization.risk_tier != capability.risk:
        reasons.append("authorization risk tier does not match the selected capability")
    if capability.risk != "low":
        reasons.append("only low-risk capabilities are executable in this slice")
    if capability.name != IntentDigestCapability.name:
        reasons.append("capability is not the allowlisted built-in demonstration")
    return not reasons, reasons


def _persist(record: dict[str, Any], records_dir: Path) -> Path:
    records_dir.mkdir(parents=True, exist_ok=True)
    target = records_dir / f"{record['id']}.json"
    fd, temporary = tempfile.mkstemp(prefix=f".{record['id']}-", suffix=".tmp", dir=records_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return target


def run_intent(intent: str, authorization: Authorization, records_dir: Path) -> tuple[dict[str, Any], Path]:
    if not intent.strip():
        raise ValueError("intent must contain non-whitespace text")

    capability = select_capability(intent, (IntentDigestCapability(),))
    record: dict[str, Any] = {
        "schema_version": 1,
        "id": str(uuid.uuid4()),
        "created_at": now_utc(),
        "updated_at": None,
        "intent": intent,
        "status": "CREATED",
        "epistemic": [
            {"state": "DECISION", "claim": "Use the first matching registered capability."},
            {"state": "HYPOTHESIS", "claim": "An intent digest safely demonstrates the control flow."},
            {"state": "PENDING", "claim": "A human must judge whether the demonstration is useful."},
        ],
        "authorization": asdict(authorization),
        "risk": {"tier": capability.risk if capability else "unknown", "rollback": "Delete this local work record."},
        "capability": {"selected": capability.name if capability else None, "interface": "Capability", "provider": "builtin"},
        "policy": {"allowed": False, "reasons": []},
        "execution": None,
        "verification": None,
        "evidence": [],
        "human_gate": {"reached": False, "reason": None},
    }
    record["updated_at"] = now_utc()
    path = _persist(record, records_dir)

    if capability is None:
        record["status"] = "NO_CAPABILITY"
        record["policy"]["reasons"] = ["no capability supports the intent"]
        record["human_gate"] = {"reached": True, "reason": "Human direction is required to add or choose a capability."}
    else:
        allowed, reasons = policy_gate(capability, authorization)
        record["policy"] = {"allowed": allowed, "reasons": reasons}
        record["evidence"].append({"kind": "policy_decision", "allowed": allowed, "reasons": reasons})
        if not allowed:
            record["status"] = "POLICY_BLOCKED"
            record["human_gate"] = {"reached": True, "reason": "A human must provide valid capability-scoped authorization."}
        else:
            result = capability.execute(intent)
            record["execution"] = {"status": "COMPLETED", "result": result}
            record["evidence"].append({"kind": "execution_result", "capability": capability.name, "value": result})
            verified, detail = capability.verify(intent, result)
            record["verification"] = {"passed": verified, "method": "deterministic recomputation", "detail": detail}
            record["evidence"].append({"kind": "verification", "passed": verified, "detail": detail})
            record["epistemic"].append({"state": "FINDING", "claim": detail})
            if verified:
                record["status"] = "HUMAN_TEST_PENDING"
                record["human_gate"] = {"reached": True, "reason": "Machine verification passed; genuine human usefulness testing remains."}
            else:
                record["status"] = "VERIFICATION_FAILED"
                record["human_gate"] = {"reached": True, "reason": "A human must inspect the verification failure."}

    record["updated_at"] = now_utc()
    return record, _persist(record, records_dir)
