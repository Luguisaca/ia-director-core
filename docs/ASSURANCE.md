# Assurance boundaries

IA Director Core is experimental software. This document states the public boundaries of what the current implementation and tests establish. It is not a security, privacy, compliance or product certification.

## Demonstrated by the repository tests

The current regression suite covers bounded properties including:

- explicit work-contract completeness checks;
- capability admission/selection behavior for repository-owned fixtures;
- separation of selection from human authorization;
- target/effect/data-destination/risk constraints;
- action-bound approval for material-risk fixture actions;
- rejection of untrusted descriptive metadata as authority;
- shell-free local process invocation with timeout/output bounds;
- verification failure not becoming successful completion;
- minimized persistence of raw directed payload/results;
- interruption detection and non-automatic retry.

These claims are limited to the tested implementation and fixtures.

## Not established

The repository does not by itself establish safe or supported operation for:

- real remote administration;
- privileged or destructive execution;
- production workloads;
- strong user identity/authentication;
- universal target identity;
- rollback of arbitrary external actions;
- handling of every secret or regulated data class;
- legal/regulatory compliance for a deployment;
- protection against a compromised host, interpreter or supply chain.

Those properties require workload- and environment-specific evidence.

## Trust boundaries

Deployments should keep distinct:

- human intent and human authority;
- policy/selection logic;
- capability/executor;
- execution target and environment;
- data entering or leaving a trust boundary;
- verification/evidence;
- repository and software supply chain.

Technical access is not authorization. Descriptive capability metadata and tool/model output are untrusted input for authority decisions.

## Data

Directed execution is designed to minimize persistence of raw payload/results and to make allowed data destinations explicit. This does not replace workload-specific classification, retention/deletion, secret handling, isolation or privacy requirements.

Do not place credentials, secrets or unrelated sensitive host data in repository fixtures or evidence.

## Dependencies and distribution

The package currently has no third-party runtime dependencies. Its build backend requires setuptools. Python and build-tool licensing remain their respective upstream licenses.

IA Director Core is distributed under PolyForm Noncommercial License 1.0.0. See `LICENSE` for the authoritative terms reference and required notice.

## Reporting security concerns

Do not publish credentials, exploit details affecting third parties, or sensitive environment data in a public issue. Until a private security-reporting channel is configured for the repository, withhold sensitive details and contact the repository owner through an agreed private channel.
