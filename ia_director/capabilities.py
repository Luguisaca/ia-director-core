"""Experimental discovery/execution layer for EXP-001.

Discovery is intentionally explicit and bounded. Providers return capabilities
with evidence plus an executor. Nothing discovered is automatically authorized.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from shutil import which
from typing import Callable, Iterable, Protocol

from .selection import CapabilityEvidence, WorkContract, select_capability


Executor = Callable[[str], str]
VerificationResult = bool | tuple[bool, str]
Verifier = Callable[[str, str], VerificationResult]


def normalize_verification(result: VerificationResult) -> tuple[bool, str | None]:
    if isinstance(result, tuple):
        return result[0], result[1]
    return result, None


@dataclass(frozen=True)
class DiscoveredCapability:
    evidence: CapabilityEvidence
    execute: Executor
    verify: Verifier


@dataclass(frozen=True)
class CapabilityCharacterization:
    capability: str
    status: str
    proven_features: frozenset[str]
    observations: tuple[str, ...]
    adapter: str | None = None


def characterize_capability(
    capability: DiscoveredCapability,
    *,
    proven_features: Iterable[str] = (),
    observations: Iterable[str] = (),
    adapter: str | None = None,
) -> CapabilityCharacterization:
    """Record probe evidence without promoting presence into competence.

    Characterization is intentionally separate from discovery and authorization.
    A transport/adapter failure is evidence about that invocation path, not
    automatic evidence that the underlying model/tool capability is unusable.
    """
    features = frozenset(proven_features)
    advertised = capability.evidence.features
    if not features <= advertised:
        unknown = ", ".join(sorted(features - advertised))
        raise ValueError(f"cannot prove unadvertised features: {unknown}")
    return CapabilityCharacterization(
        capability=capability.evidence.name,
        status="CHARACTERIZED" if features else "PRESENCE_ONLY",
        proven_features=features,
        observations=tuple(observations),
        adapter=adapter,
    )


class CapabilityProvider(Protocol):
    def discover(self) -> Iterable[DiscoveredCapability]: ...


@dataclass(frozen=True)
class ExecutionRecord:
    selected: str | None
    considered: tuple[str, ...]
    result: str | None
    verified: bool
    status: str


@dataclass(frozen=True)
class StrategyAttempt:
    capability: str
    status: str
    reason: str


@dataclass(frozen=True)
class StrategyRecord:
    selected: str | None
    considered: tuple[str, ...]
    attempts: tuple[StrategyAttempt, ...]
    status: str
    handoff: dict


class BuiltinProvider:
    """Real local deterministic capabilities shipped with this experiment."""

    def discover(self) -> tuple[DiscoveredCapability, ...]:
        digest = DiscoveredCapability(
            evidence=CapabilityEvidence(
                name="builtin.sha256",
                features=frozenset({"digest"}),
                effects=frozenset(),
                destinations=frozenset({"local"}),
                risk="low",
                estimated_cost=0.0,
                complexity=1,
                provenance="ia-director-core:builtin",
                verification="sha256-recompute",
            ),
            execute=lambda text: sha256(text.encode("utf-8")).hexdigest(),
            verify=lambda text, result: sha256(text.encode("utf-8")).hexdigest() == result,
        )
        normalize = DiscoveredCapability(
            evidence=CapabilityEvidence(
                name="builtin.normalize",
                features=frozenset({"normalize"}),
                effects=frozenset(),
                destinations=frozenset({"local"}),
                risk="low",
                estimated_cost=0.0,
                complexity=1,
                provenance="ia-director-core:builtin",
                verification="normalization-recompute",
            ),
            execute=lambda text: " ".join(text.split()),
            verify=lambda text, result: " ".join(text.split()) == result,
        )
        return digest, normalize


class EnvironmentToolProvider:
    """Bounded read-only discovery of known executable tools on PATH.

    This does not crawl the machine, install anything, or infer permissions.
    Discovered tools expose only an inventory feature until an adapter proves
    a safe executable capability.
    """

    _KNOWN = ("python3", "python", "git", "curl", "node", "rg", "codex", "ollama", "wsl")

    def discover(self) -> tuple[DiscoveredCapability, ...]:
        found: list[DiscoveredCapability] = []
        for tool in self._KNOWN:
            path = which(tool)
            if path is None:
                continue
            found.append(
                DiscoveredCapability(
                    evidence=CapabilityEvidence(
                        name=f"environment.tool.{tool}",
                        features=frozenset({"tool-present", f"tool:{tool}"}),
                        effects=frozenset(),
                        destinations=frozenset({"local"}),
                        risk="low",
                        estimated_cost=0.0,
                        complexity=1,
                        provenance=path,
                        verification="PATH executable presence",
                    ),
                    execute=lambda text, value=path: value,
                    verify=lambda text, result, value=path: result == value,
                )
            )
        return tuple(found)


class StaticProvider:
    """Test/reuse boundary for adapters without making a registry architecture."""

    def __init__(self, capabilities: Iterable[DiscoveredCapability]):
        self._capabilities = tuple(capabilities)

    def discover(self) -> tuple[DiscoveredCapability, ...]:
        return self._capabilities


def discover_capabilities(
    providers: Iterable[CapabilityProvider],
) -> tuple[DiscoveredCapability, ...]:
    discovered: list[DiscoveredCapability] = []
    seen: set[str] = set()
    for provider in providers:
        for capability in provider.discover():
            name = capability.evidence.name
            if name in seen:
                raise ValueError(f"duplicate capability identity: {name}")
            seen.add(name)
            discovered.append(capability)
    return tuple(discovered)


def execute_contract(
    contract: WorkContract,
    payload: str,
    providers: Iterable[CapabilityProvider],
) -> ExecutionRecord:
    """Discover, select, execute once, and verify independently of execute()."""
    capabilities = discover_capabilities(providers)
    selected, decisions = select_capability(
        contract, (capability.evidence for capability in capabilities)
    )
    considered = tuple(decision.capability for decision in decisions)
    if selected is None:
        return ExecutionRecord(None, considered, None, False, "NO_ADMISSIBLE_CAPABILITY")

    chosen = next(item for item in capabilities if item.evidence.name == selected.name)
    result = chosen.execute(payload)
    verified, _detail = normalize_verification(chosen.verify(payload, result))
    return ExecutionRecord(
        selected.name,
        considered,
        result,
        verified,
        "VERIFIED" if verified else "VERIFICATION_FAILED",
    )


def execute_contract_adaptive(
    contract: WorkContract,
    payload: str,
    providers: Iterable[CapabilityProvider],
) -> StrategyRecord:
    """Discover and try admissible candidates until one verifies.

    This is a bounded strategy experiment, not a universal planner. Selection
    remains contract/evidence driven; a failed verifier is evidence to reject
    that candidate for this run rather than a reason to ask the human to choose
    another already-discovered option.
    """
    capabilities = discover_capabilities(providers)
    decisions = [
        select_capability(contract, [item.evidence])[1][0]
        for item in capabilities
    ]
    considered = tuple(item.capability for item in decisions)
    admitted = sorted(
        (
            (decision.score, capability)
            for decision, capability in zip(decisions, capabilities)
            if decision.admissible and decision.score is not None
        ),
        key=lambda item: item[0],
    )
    attempts: list[StrategyAttempt] = []
    for _score, capability in admitted:
        result = capability.execute(payload)
        if normalize_verification(capability.verify(payload, result))[0]:
            attempts.append(StrategyAttempt(capability.evidence.name, "VERIFIED", "independent verifier passed"))
            handoff = {
                "selected": capability.evidence.name,
                "why": "lowest-cost/complexity admissible candidate that independently verified",
                "considered": considered,
                "attempts": tuple({"capability": x.capability, "status": x.status, "reason": x.reason} for x in attempts),
                "estimated_cost": capability.evidence.estimated_cost,
                "risk": capability.evidence.risk,
                "data_destinations": tuple(sorted(capability.evidence.destinations or ())),
                "human_action_required": None,
            }
            return StrategyRecord(capability.evidence.name, considered, tuple(attempts), "VERIFIED", handoff)
        attempts.append(StrategyAttempt(capability.evidence.name, "REJECTED_AFTER_VERIFICATION", "independent verifier failed"))

    rejected = tuple(
        {"capability": d.capability, "reasons": d.reasons}
        for d in decisions if not d.admissible
    )
    handoff = {
        "selected": None,
        "why": "no discovered admissible candidate produced independently verified output",
        "considered": considered,
        "attempts": tuple({"capability": x.capability, "status": x.status, "reason": x.reason} for x in attempts),
        "rejected": rejected,
        "human_action_required": "Acquire, authorize, or provide missing capability only if further autonomous discovery cannot satisfy the contract.",
    }
    return StrategyRecord(None, considered, tuple(attempts), "NO_VERIFIED_CAPABILITY", handoff)
