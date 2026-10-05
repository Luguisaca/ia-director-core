"""Experimental bridge from WorkContract selection into the persistent Core cycle.

This slice is intentionally local and low-risk. It proves integration; it does
not authorize remote, privileged, network, or material external work.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from .accountability import ExecutionLedger
from .capabilities import CapabilityProvider, discover_capabilities
from .core import _persist, now_utc
from .selection import WorkContract, contract_issues, select_capability


@dataclass(frozen=True)
class DirectedAuthorization:
    granted: bool
    granted_by: str | None
    allowed_capabilities: frozenset[str]
    allowed_targets: frozenset[str] = frozenset()
    allowed_effects: frozenset[str] = frozenset()
    allowed_destinations: frozenset[str] = frozenset({"local"})
    max_risk: str = "low"
    approval_digest: str | None = None


_RISK = {"low": 0, "medium": 1, "high": 2}


def action_digest(capability: str, targets: frozenset[str], payload: str) -> str:
    material = json.dumps(
        {"capability": capability, "targets": sorted(targets), "payload_sha256": hashlib.sha256(payload.encode()).hexdigest()},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode()).hexdigest()


def run_contract(
    contract: WorkContract,
    payload: str,
    authorization: DirectedAuthorization,
    records_dir: Path,
    providers: tuple[CapabilityProvider, ...],
) -> tuple[dict, Path]:
    issues = contract_issues(contract)
    discovered = discover_capabilities(providers)
    if issues:
        selected, decisions = None, ()
    else:
        selected, decisions = select_capability(
            contract, [item.evidence for item in discovered]
        )
    ledger = ExecutionLedger(contract.outcome)
    record = {
        "schema_version": 3,
        "id": str(uuid.uuid4()),
        "created_at": now_utc(),
        "updated_at": None,
        "contract": {
            "outcome": contract.outcome,
            "required_features": sorted(contract.required_features),
            "allowed_effects": sorted(contract.allowed_effects),
            "allowed_destinations": sorted(contract.allowed_destinations),
            "acceptance_criteria": list(contract.acceptance_criteria),
            "targets": sorted(contract.targets),
            "max_risk": contract.max_risk,
            "max_cost": contract.max_cost,
        },
        "authorization": {
            "granted": authorization.granted,
            "granted_by": authorization.granted_by,
            "allowed_capabilities": sorted(authorization.allowed_capabilities),
            "allowed_targets": sorted(authorization.allowed_targets),
            "allowed_effects": sorted(authorization.allowed_effects),
            "allowed_destinations": sorted(authorization.allowed_destinations),
            "max_risk": authorization.max_risk,
            "approval_digest": authorization.approval_digest,
        },
        "selection": {
            "selected": selected.name if selected else None,
            "considered": [
                {
                    "capability": item.capability,
                    "admissible": item.admissible,
                    "reasons": list(item.reasons),
                }
                for item in decisions
            ],
        },
        "contract_issues": list(issues),
        "policy": {"allowed": False, "reasons": []},
        "execution": None,
        "verification": None,
        "evidence": [],
        "accountability": ledger.as_record(),
        "status": "CREATED",
        "human_gate": {"reached": False, "reason": None},
    }

    if issues:
        record["status"] = "CONTRACT_INCOMPLETE"
        record["human_gate"] = {
            "reached": False,
            "reason": "Contract requires enrichment before capability selection or execution.",
        }
        record["updated_at"] = now_utc()
        return record, _persist(record, records_dir)

    if selected is None:
        record["status"] = "CAPABILITY_RESOLUTION_REQUIRED"
        record["human_gate"] = {
            "reached": False,
            "reason": "No current capability is admissible; discovery/reuse/composition/build resolution remains IA work.",
        }
        record["updated_at"] = now_utc()
        return record, _persist(record, records_dir)

    reasons = []
    if not authorization.granted:
        reasons.append("explicit authorization was not granted")
    if not authorization.granted_by:
        reasons.append("authorizing human identity is missing")
    if selected.name not in authorization.allowed_capabilities:
        reasons.append("selected capability is outside authorization")
    if not contract.targets <= authorization.allowed_targets:
        reasons.append("contract target is outside authorization")
    if (
        selected.risk not in _RISK
        or authorization.max_risk not in _RISK
        or _RISK[selected.risk] > _RISK[authorization.max_risk]
    ):
        reasons.append("selected capability risk exceeds authorization")
    if selected.effects is None or not selected.effects <= authorization.allowed_effects:
        reasons.append("selected capability effects exceed authorization")
    if selected.destinations is None or not selected.destinations <= authorization.allowed_destinations:
        reasons.append("selected capability data destination exceeds authorization")
    if selected.risk != "low":
        expected = action_digest(selected.name, contract.targets, payload)
        if authorization.approval_digest != expected:
            reasons.append("material-risk action lacks exact action-bound approval")

    record["policy"] = {"allowed": not reasons, "reasons": reasons}
    record["evidence"].append(
        {"kind": "policy_decision", "allowed": not reasons, "reasons": reasons}
    )
    if reasons:
        record["status"] = "POLICY_BLOCKED"
        record["human_gate"] = {
            "reached": True,
            "reason": "Execution requires authorization matching the selected capability.",
        }
        record["updated_at"] = now_utc()
        return record, _persist(record, records_dir)

    record["status"] = "EXECUTION_PENDING"
    record["updated_at"] = now_utc()
    path = _persist(record, records_dir)

    runtime = next(item for item in discovered if item.evidence.name == selected.name)
    result = runtime.execute(payload)
    verified = runtime.verify(payload, result)
    result_digest = hashlib.sha256(result.encode("utf-8")).hexdigest()
    record["execution"] = {
        "status": "COMPLETED",
        "result_persisted": False,
        "result_sha256": result_digest,
    }
    record["verification"] = {
        "passed": verified,
        "method": selected.verification,
    }
    record["evidence"].extend(
        [
            {
                "kind": "execution_result",
                "capability": selected.name,
                "result_persisted": False,
                "result_sha256": result_digest,
            },
            {"kind": "verification", "passed": verified, "method": selected.verification},
        ]
    )
    ledger.record_test(
        selected.verification or "capability verification",
        "PASS" if verified else "FAIL",
        f"result_sha256:{result_digest}",
    )
    record["accountability"] = ledger.as_record()
    if verified:
        record["status"] = "HUMAN_TEST_PENDING"
        record["human_gate"] = {
            "reached": True,
            "reason": "Machine verification passed; human usefulness remains authoritative.",
        }
    else:
        record["status"] = "VERIFICATION_FAILED"
        record["human_gate"] = {
            "reached": False,
            "reason": "Machine verification failed; do not promote to human testing.",
        }
    record["updated_at"] = now_utc()
    return record, _persist(record, records_dir)

def reconcile_interrupted_record(path: Path) -> dict:
    """Make an interrupted directed record explicit without retrying execution."""
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("status") == "EXECUTION_PENDING":
        record["status"] = "INTERRUPTED"
        record["updated_at"] = now_utc()
        record["human_gate"] = {
            "reached": False,
            "reason": "Execution was interrupted; revalidate contract, authority, target, and capability before retry.",
        }
        _persist(record, path.parent)
    return record
