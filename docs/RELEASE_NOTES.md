# Release notes (experimental)

## Capability selection: ambiguous identities

Capability selection now rejects every candidate sharing a capability name with another candidate in the same selection request. The decision trail retains rejection reasons, while unambiguous admissible alternatives remain eligible. This prevents a name-based lookup from returning an executor other than the one evaluated.

The behavior is covered by four additional regression tests. The Python unit suite passes with 106 tests on an isolated Windows checkout.

### Scope and limitations

This is a bounded correctness and authorization improvement, not evidence of autonomous software authorship, end-to-end functional QA, or production readiness. Integration depends on repository checks and independent review. No model installation or inference is required for this update.
