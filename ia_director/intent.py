"""Intent enrichment without inventing human authority."""

from __future__ import annotations

from dataclasses import dataclass

from .selection import WorkContract


@dataclass(frozen=True)
class IntentResolution:
    contract: WorkContract | None
    inferred: tuple[str, ...]
    human_decisions_required: tuple[str, ...]


def derive_development_contract(
    intent: str,
    *,
    target: str,
    allowed_destinations: frozenset[str] = frozenset({"local"}),
    max_risk: str = "low",
) -> IntentResolution:
    """Derive a conservative development contract from a non-empty human intent.

    This deliberately derives only transversal engineering acceptance properties.
    Product choices not stated by the human remain outside this helper.
    """
    normalized = " ".join(intent.split())
    if not normalized:
        return IntentResolution(None, (), ("desired outcome is missing",))
    if not target.strip():
        return IntentResolution(None, (), ("authorized development target is missing",))
    criteria = (
        "requested outcome is functionally demonstrable",
        "applicable automated verification passes",
        "material failures and limitations are reported",
        "persistent environment changes are accounted for",
        "deliverable is ready for human usefulness testing",
    )
    contract = WorkContract(
        outcome=normalized,
        required_features=frozenset({"software-development"}),
        allowed_effects=frozenset({"read", "create", "modify", "delete-project-artifacts"}),
        allowed_destinations=allowed_destinations,
        acceptance_criteria=criteria,
        targets=frozenset({target}),
        max_risk=max_risk,
        max_cost=0.0,
    )
    return IntentResolution(
        contract,
        ("transversal development acceptance criteria", "local-first data destination", "zero external service cost"),
        (),
    )
