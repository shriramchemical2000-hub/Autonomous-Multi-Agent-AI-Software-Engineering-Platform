# ForgeAI Evaluation Protocol

ForgeAI's evaluation is evidence-based and avoids scoring a model by whether its prose sounds convincing.

## Current automated checks

- Pydantic contract validation and malformed-output handling.
- Approval gates and workflow routing with fake model providers.
- Artifact persistence, versioning, and review audit events.
- Safe source-bundle path and size validation.
- Docker runner guardrails, bounded output/time, and test selection.
- Bounded repair proposals that preserve test files.
- Delivery readiness scoring and ZIP export integrity.

## Manual evaluation scenarios

1. Give the Requirements Analyst an ambiguous brief and inspect open questions and assumptions.
2. Reject requirements and confirm architecture remains locked.
3. Approve requirements but reject architecture and confirm UI/UX remains locked.
4. Approve all upstream artifacts and inspect source bundle completeness.
5. Supply a deliberately failing test and confirm the report references the exact source artifact.
6. Request a repair and confirm test files remain byte-for-byte unchanged.
7. Approve the candidate and rerun regression tests; do not call the repair successful until the run passes.
8. Change the source bundle and confirm an older passing test report no longer counts as current evidence.
9. Export a delivery archive and inspect its manifest, artifact versions, audit events, and source files.
10. Confirm the deployment status remains NOT DEPLOYED until an operator actually deploys and verifies a staging environment.

## Metrics to capture in a future benchmark

- Requirements completeness and acceptance-criteria traceability.
- Architecture consistency with requirements.
- Source bundle importability and functional acceptance pass rate.
- Test pass rate on a fixed held-out benchmark.
- Defect severity and false-positive rate in code review.
- Repair success rate after regression execution.
- Token/cost consumption and end-to-end latency.
- Human approval/change-request rate and review time.

The current Delivery Center computes a deterministic artifact-evidence score. It does not claim benchmark accuracy, test coverage, or model quality scores without a measured dataset.
