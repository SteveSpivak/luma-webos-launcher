# Cross-platform agent operating contract (v1)

Applies to Arena, Claude, Codex, Gemini and local scripts. This file is an additive operating guide, not a replacement for existing project ADRs, safety rules or CI.

## Start every task
1. Inspect repository identity, clean/dirty state, branch, full SHA, upstream and tool availability. Never reset a dirty tree. Inspect existing implementation, tests, owners and proven patterns before creating a new component.
2. Record exact input SHAs for every involved repository, the contract ID/version, the current known failures, and which environment can execute each gate. Refresh those pins whenever a branch advances.
3. Define the smallest bounded objective, owner, interfaces, acceptance tests and rollback. Work in a dedicated branch, not another agent's active branch.
4. Execute deterministic search, parsing, hashing and tests with local scripts. Use the model for hypotheses, architecture and diagnosis. Avoid creating a second router, memory store, governor or scheduler if an existing component can own the behavior.

## Evidence and honesty
Evidence labels are PROVEN_CODE (inspected implementation), TESTED_OFFLINE (actual run), COMPILED (actual compiler gate), MEASURED_DEVICE (identified device/run), INFERRED, PROPOSED, UNKNOWN and NOT_RUN. No label is promoted without matching receipts. A static analyzer is not a Rust compiler. A synthetic test is not TV behavior. A JS reference mirror is not an independently verified Rust consumer.

For hashes: record exact input bytes, algorithm, expected answer, recomputation method, and artifact SHA-256. Never transcribe constants without recomputing. For performance claims: record process identity, device profile, environment, time window, sample counts, units, raw-data path, GC/thermal/network confounders, and uncertainty. Do not combine JS heap, GPU budgets and system RAM as interchangeable numbers.

## Test and change sequence
BEFORE evidence -> focused failure reproducer -> smallest patch -> focused proof -> negative/mutation test -> relevant regression -> integration -> device canary only when approved. Zero tests discovered is not success. A baseline-stable red suite is NOT release-ready. Capture command, exit code, full SHA and logs for each gate.

Agent-written tests must be falsifiable. Inject invalid hashes, protocol sizes, malformed input, invalid deep links and unexpected lifecycle transitions and prove rejection. Prefer independent producer/consumer conformance over two copies of the same implementation.

## Safety and cross-repository handoff
Do not modify another repository, production bridge file, installed TV application, firmware, DNS/firewall settings, credentials or physical device without its owner's explicit scope/authorization. Read-only local scans and tests are the default. Commit and push only your own branch. Do not force-push shared work. Make PRs against the recorded integration owner.

Each handoff includes: base/head full SHA, branch, changed paths, contract versions, test commands and statuses (PASS/FAIL/BLOCKED/NOT_RUN), existing baseline failures, receipt paths + hashes, unresolved hypotheses, rollback, and next bounded action. Do not claim a future test has passed.

## Built-in portable verifier
`python3 scripts/agent_receipt.py snapshot` records local identity without network or mutation.
`python3 scripts/agent_receipt.py self-test` checks the receipt validator.
`python3 scripts/agent_receipt.py verify <receipt.json>` validates statuses and artifact hashes. The validator does NOT execute the test it describes; only accepts evidence artifacts and cannot itself prove that an asserted test ran.

Example receipt schema: `tv-agent/gate-receipt/v1` with repo, branch, head_sha (40 hex), gate_id, command, status, evidence_level and artifacts [{path, sha256}]. Artifacts must exist under the repository root. Gate statuses must evolve when verified; never permanently assert a gate remains NOT_RUN.

## Luma owner rules
Use docs/architecture/component-map.md to identify canonical owners before editing Rust state, renderer or platform services. Rustfmt, cargo check, cargo test, feature matrix and CI are authoritative for compilation; scripts/sandbox_verify.py is heuristic supplementary evidence only.

Luma consumes Nuvio's bridge; do not write the production LCKV bridge, including from labs/seeding tools. Verify strict parser limits, exact bytes, hashes, stable card IDs, tombstone semantics and accepted Nuvio deep links with producer-owned fixtures. Keep device deploy separate from compiler-ready and integration-ready gates. Memory/renderer changes need baseline and lifecycle telemetry, not arbitrary glFlush/malloc_trim delays.
