"""Experimental adapters from external capability metadata.

Adapters preserve what a source actually states. They must not turn descriptive
metadata into authorization, safety, execution, or verification claims.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .selection import CapabilityEvidence, WorkContract


def agent_skill_evidence(metadata: Mapping[str, Any], *, provenance: str) -> CapabilityEvidence:
    """Map Agent Skills frontmatter already parsed by a standards-aware loader.

    Agent Skills name/description advertise procedural competence. The standard
    does not prove runtime effects, destinations, risk, cost, or outcome
    verification, so those fields intentionally remain unknown.
    """
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Agent Skill metadata requires non-empty name")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Agent Skill metadata requires non-empty description")

    features = {"agent-skill", f"skill:{name.strip()}"}
    return CapabilityEvidence(
        name=f"agent-skill.{name.strip()}",
        features=frozenset(features),
        effects=None,
        destinations=None,
        risk=None,
        estimated_cost=None,
        complexity=1,
        provenance=provenance,
        verification=None,
    )


def agent_harness_work_contract(
    portable: Mapping[str, Any],
    *,
    targets: frozenset[str] = frozenset(),
    allowed_effects: frozenset[str] = frozenset(),
    allowed_destinations: frozenset[str] = frozenset(),
    max_risk: str = "unknown",
    max_cost: float | None = None,
) -> WorkContract:
    """Adapt the overlapping Portable Contract v2 fields without inventing authority.

    Execution constraints absent from the portable contract remain absent or
    unknown unless supplied by a separate trusted authority/policy source.
    """
    objective = portable.get("objective")
    capabilities = portable.get("capabilities")
    if not isinstance(objective, Mapping) or not isinstance(capabilities, Mapping):
        raise ValueError("portable contract requires objective and capabilities")

    goal = objective.get("goal")
    done_when = objective.get("done_when")
    required = capabilities.get("required")
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("portable contract objective.goal is required")
    if not isinstance(done_when, list) or not all(isinstance(x, str) and x.strip() for x in done_when):
        raise ValueError("portable contract objective.done_when must contain strings")
    if not isinstance(required, list) or not all(isinstance(x, str) and x.strip() for x in required):
        raise ValueError("portable contract capabilities.required must contain strings")

    return WorkContract(
        outcome=goal.strip(),
        required_features=frozenset(x.strip() for x in required),
        allowed_effects=allowed_effects,
        allowed_destinations=allowed_destinations,
        acceptance_criteria=tuple(x.strip() for x in done_when),
        targets=targets,
        max_risk=max_risk,
        max_cost=max_cost,
    )
