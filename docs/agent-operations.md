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

## Agent access boundaries and private-repository isolation (mandatory)

Repository visibility and agent credentials are independent facts. Never infer access from a URL, a repo name, a task description, an assistant's prior success, or another agent's permissions. Discover capabilities at task start with a read-only probe and record the result for EACH repository as `READABLE`, `DENIED`, `NOT_FOUND`, or `NOT_PROBED`; a failure is not permission to attempt bypasses.

| Executor | Authorized working scope | Cross-repository behavior |
| --- | --- | --- |
| ChatGPT (connected GitHub) | Repositories granted to the active connection; may include private repositories | Inspect only through authorized connector permissions; prepare sanitized cross-repo handoffs when needed |
| Local Claude, Codex, Kimi, Agy or other local CLI models | Checked-out worktrees and remotes accessible through that machine's credentials | May compile and verify across authorized local clones; never assume every model/process shares credentials or filesystem access |
| Arena cloud agent | Its explicitly provided working repository and other *public* accessible sources, subject to actual sandbox permissions | Treat unrelated private repositories as `DENIED` by default. Do not fetch, enumerate, guess URLs, ask for credentials, or claim cross-repo verification |
| CI runners | Checked-out repository and explicitly authorized artifacts/dependencies | Run only declared contracts and artifact checks; permission failures are `BLOCKED` |

**Visibility-sensitive workspace notes:** LG-TV and nuvio-perf-lab are private in the reviewed GitHub state; luma-webos-launcher is public. Visibility may change, so treat these as observations, not a timeless policy.

**Safe work allocation:** Private-repo inspection, cross-repo diffs, source-integrity checks and end-to-end integration are owned by an authorized local agent or ChatGPT connector. Arena works on its current repository only and may validate a *sanitized, intentionally exported* contract packet. Do not give Arena raw private source trees, logs containing tokens, device addresses, account identifiers, or unrestricted GitHub credentials.

**Handoff boundary:** The owner of a private repository exports the minimum nonsecret interface contract or test vector needed by the receiving agent, accompanied by source provenance (repo identifier if acceptable to disclose, pinned SHA, contract version, SHA-256, permitted use, and redaction review). The public repository must only receive explicitly approved public contract material. Do not publish private commits, confidential paths, private code, device telemetry or raw account state through a public PR merely to help an agent.

**Inaccessible dependency:** Mark dependent gates `BLOCKED` with reason `REPOSITORY_ACCESS_DENIED` and name the authorized verifier. Never convert an agent's inability to check a private repository into PASS, assume another agent's conclusions are current, or repeatedly retry a denied endpoint. A signed-off local receipt may be consumed as evidence of what THAT verifier ran; it is not a substitute for the Arena agent personally reading the source.

**Operational flow:** 1) discover current working repo and available permissions; 2) work within that boundary; 3) request a scoped, sanitized contract packet from the authorized local owner when necessary; 4) publish branch-local evidence; 5) let the authorized integration verifier independently check both repositories and decide promotion. No parallel shared-branch writes.

## Executable access and handoff addendum (v2)

Do not confuse repository visibility with provider permission. Run `python3 scripts/agent_receipt.py snapshot --executor <arena|local|chatgpt|ci>` first. Its capability record proves only the current checkout; cross-repository and network access remain NOT_PROBED until independently observed. The script never probes a remote or TV. Treat private dependencies as BLOCKED when denied and never attempt permission bypass.

Use [agent-charter.md](agent-charter.md) for responsibility, phase gates, privacy and approvals; use [agent-handoff.template.json](agent-handoff.template.json) for a scoped work order. The template contains placeholders, never actual authorized SHAs. Never paste private source into a public repository as a workaround for Arena access. A public sanitized contract packet needs explicit approval and provenance.

`python3 scripts/agent_receipt.py verify <receipt.json>` validates structure, exit-code declaration and local artifact SHA-256. It cannot prove that the exit code represents a real executed command; require the raw/test log and an independent verifier for high-risk claims. Status transitions are evidence-driven, not permanently pinned to NOT_RUN.
