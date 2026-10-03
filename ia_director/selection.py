"""Experimental contract-driven capability admission and selection.

This module is deliberately separate from the proven demo flow in core.py.
Its types are experiment fixtures, not an approved universal architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable


@dataclass(frozen=True)
class WorkContract:
    outcome: str
    required_features: frozenset[str]
    allowed_effects: frozenset[str]
    allowed_destinations: frozenset[str]
    acceptance_criteria: tuple[str, ...] = ()
    targets: frozenset[str] = frozenset()
    max_risk: str = "low"
    max_cost: float | None = None


@dataclass(frozen=True)
class CapabilityEvidence:
    name: str
    features: frozenset[str]
    effects: frozenset[str] | None
    destinations: frozenset[str] | None
    risk: str | None
    estimated_cost: float | None
    complexity: int
    provenance: str | None
    verification: str | None


@dataclass(frozen=True)
class CandidateDecision:
    capability: str
    admissible: bool
    reasons: tuple[str, ...]
    score: tuple[float, int, str] | None = None


_RISK = {"low": 0, "medium": 1, "high": 2}


def evaluate_candidate(contract: WorkContract, candidate: CapabilityEvidence) -> CandidateDecision:
    """Evaluate one candidate only from explicit contract/evidence."""
    reasons: list[str] = []

    missing_features = contract.required_features - candidate.features
    if missing_features:
        reasons.append("missing required features: " + ", ".join(sorted(missing_features)))

    if candidate.effects is None:
        reasons.append("effects evidence is missing")
    elif not candidate.effects <= contract.allowed_effects:
        reasons.append("effects exceed contract")

    if candidate.destinations is None:
        reasons.append("data destination evidence is missing")
    elif not candidate.destinations <= contract.allowed_destinations:
        reasons.append("data destination exceeds contract")

    if candidate.risk not in _RISK:
        reasons.append("risk evidence is missing or unknown")
    elif contract.max_risk not in _RISK or _RISK[candidate.risk] > _RISK[contract.max_risk]:
        reasons.append("risk exceeds contract")

    if candidate.provenance is None:
        reasons.append("provenance evidence is missing")
    if candidate.verification is None:
        reasons.append("verification evidence is missing")

    if contract.max_cost is not None:
        if candidate.estimated_cost is None:
            reasons.append("cost evidence is missing")
        elif candidate.estimated_cost > contract.max_cost:
            reasons.append("cost exceeds contract")

    if reasons:
        return CandidateDecision(candidate.name, False, tuple(reasons))

    # This is an experimental deterministic preference, not a universal formula:
    # among candidates already proven admissible, prefer lower declared cost,
    # then lower complexity. Name is only a stable tie-breaker.
    cost = candidate.estimated_cost if candidate.estimated_cost is not None else 0.0
    return CandidateDecision(candidate.name, True, (), (cost, candidate.complexity, candidate.name))


def select_capability(
    contract: WorkContract, candidates: Iterable[CapabilityEvidence]
) -> tuple[CapabilityEvidence | None, tuple[CandidateDecision, ...]]:
    """Return the best admitted candidate and the full explainable decision trail."""
    materialized = tuple(candidates)
    decisions = tuple(evaluate_candidate(contract, item) for item in materialized)
    by_name = {item.name: item for item in materialized}
    admitted = [item for item in decisions if item.admissible]
    if not admitted:
        return None, decisions
    selected = min(admitted, key=lambda item: item.score)
    return by_name[selected.capability], decisions



def select_capability_set(
    contract: WorkContract, candidates: Iterable[CapabilityEvidence]
) -> tuple[tuple[CapabilityEvidence, ...] | None, tuple[str, ...]]:
    """Find the smallest admissible evidence set whose features cover the contract.

    This selects a composition; it does not plan, order, authorize, or execute
    a workflow. Candidate safety constraints are checked independently and
    feature coverage is evaluated only after those checks pass.
    """
    materialized = tuple(candidates)
    safe: list[CapabilityEvidence] = []
    rejected: list[str] = []

    # Check non-feature contract constraints per capability. A temporary
    # contract with no required features prevents partial feature coverage from
    # being mistaken for a safety failure.
    safety_contract = WorkContract(
        outcome=contract.outcome,
        required_features=frozenset(),
        allowed_effects=contract.allowed_effects,
        allowed_destinations=contract.allowed_destinations,
        max_risk=contract.max_risk,
        max_cost=None,
    )
    for item in materialized:
        decision = evaluate_candidate(safety_contract, item)
        if decision.admissible:
            safe.append(item)
        else:
            rejected.append(f"{item.name}: " + "; ".join(decision.reasons))

    for size in range(1, len(safe) + 1):
        admitted: list[tuple[tuple[float, int, tuple[str, ...]], tuple[CapabilityEvidence, ...]]] = []
        for group in combinations(safe, size):
            features = frozenset().union(*(item.features for item in group))
            if not contract.required_features <= features:
                continue
            if contract.max_cost is not None:
                if any(item.estimated_cost is None for item in group):
                    continue
                total_cost = sum(item.estimated_cost or 0.0 for item in group)
                if total_cost > contract.max_cost:
                    continue
            else:
                total_cost = sum(item.estimated_cost or 0.0 for item in group)
            complexity = sum(item.complexity for item in group)
            names = tuple(sorted(item.name for item in group))
            admitted.append(((total_cost, complexity, names), group))
        if admitted:
            _, chosen = min(admitted, key=lambda entry: entry[0])
            return chosen, tuple(rejected)

    return None, tuple(rejected)


def contract_issues(contract: WorkContract) -> tuple[str, ...]:
    """Return material omissions that make a contract unready for execution."""
    issues: list[str] = []
    if not contract.outcome.strip():
        issues.append("outcome is missing")
    if not contract.required_features:
        issues.append("required capability features are missing")
    if not contract.acceptance_criteria:
        issues.append("acceptance criteria are missing")
    if not contract.targets:
        issues.append("execution target is missing")
    if not contract.allowed_destinations:
        issues.append("allowed data destinations are missing")
    if contract.max_risk not in _RISK:
        issues.append("maximum risk tier is unknown")
    if contract.max_cost is not None and contract.max_cost < 0:
        issues.append("maximum cost cannot be negative")
    return tuple(issues)
