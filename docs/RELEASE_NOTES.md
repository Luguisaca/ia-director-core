# Release notes (experimental)

## Capability selection: ambiguous identities

Capability selection now rejects every candidate sharing a capability name with another candidate in the same selection request. The decision trail retains rejection reasons, while unambiguous admissible alternatives remain eligible. This prevents a name-based lookup from returning an executor other than the one evaluated.

The behavior is covered by four additional regression tests. The Python unit suite passes with 106 tests on an isolated Windows checkout.

### Scope and limitations

This is a bounded correctness and authorization improvement, not evidence of autonomous software authorship, end-to-end functional QA, or production readiness. Integration depends on repository checks and independent review. No model installation or inference is required for this update.

## Capability selection: bounded cost evidence

Candidate admission now rejects malformed, negative and non-finite cost evidence and invalid budget limits. Capability compositions compare decimal costs exactly and reject non-finite totals, preventing rounding from admitting an over-budget combination. Ambiguous capability names remain rejected in single-candidate selection.

The changes add cost-validation and boundary-regression tests. On a clean public checkout, the Python suite passed 118 tests, and the public-surface, compile and diff-hygiene checks passed.

This change improves an experimental selection boundary; it does not validate autonomous application authoring or production readiness.
