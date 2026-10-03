"""Bounded capability discovery and execution layer.

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
Verifier = Callable[[str, str], bool]


@dataclass(frozen=True)
class DiscoveredCapability:
    evidence: CapabilityEvidence
    execute: Executor
    verify: Verifier


class CapabilityProvider(Protocol):
    def discover(self) -> Iterable[DiscoveredCapability]: ...


@dataclass(frozen=True)
class ExecutionRecord:
    selected: str | None
    considered: tuple[str, ...]
    result: str | None
    verified: bool
    status: str


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

    _KNOWN = ("python3", "git", "curl", "node", "rg")

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
    verified = chosen.verify(payload, result)
    return ExecutionRecord(
        selected.name,
        considered,
        result,
        verified,
        "VERIFIED" if verified else "VERIFICATION_FAILED",
    )
