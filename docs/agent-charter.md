# Multi-agent engineering charter (2026-11-06, v1)

## Objective and boundaries
Make cross-platform work reproducible across ChatGPT, local Claude/Codex/Kimi/Agy, Arena and CI without transferring private repositories or sensitive device telemetry into public workspaces. Git remains source of truth; this charter adds no central scheduler, database or independent memory service.

## Responsibility and ownership
| Work | Owner | Contributor | Approval / proof |
|---|---|---|---|
| Repository truth, current SHAs, open issues | Owning repository | Authorized GitHub/local agent | Full revision pins and diff |
| Private cross-repo discovery | Authorized local agent / ChatGPT connector | Private repo maintainers | No external publication by default |
| Current-repository implementation | Branch owner (Arena or local) | Reviewer | Focused tests and code diff |
| Shared contract proposal | Producer/receiver owners together | Agent with sanitized fixtures | Both implementations and golden tests |
| Rust compilation and device-integrated tests | Authorized local agent | Luma/Nuvio owners | Compiler receipts; device approval separate |
| TV mutation, firmware, root, DNS, installation | Human TV owner | Authorized local agent | Explicit per-operation approval + rollback |
| Merge / release | Repository integration owner | CI | Gates and review |

## Capability-aware dispatch
Never assume a provider has access to another private repo. The agent checks the current checkout and records everything else as NOT_PROBED until an authorized direct read confirms access. Arena operates on its current supplied repository and authorized public sources only; no credential-sharing or bypass. A repository being public does not guarantee network availability. Private LG-TV and Nuvio information must be redacted before any transfer to public Luma.

## Work state machine
DISCOVER -> RECONCILE -> REPRODUCE -> PATCH -> VERIFY -> REVIEW -> INTEGRATE -> RELEASE.

- **DISCOVER:** working tree, exact SHA, toolchain, existing owners, permission boundaries.
- **RECONCILE:** owner contract versions, source pins, baseline failures; mark missing information BLOCKED.
- **REPRODUCE:** smallest deterministic failing check. When no reproducer is possible, document WHY.
- **PATCH:** narrow branch and bounded change; no unrelated rewrites.
- **VERIFY:** focused proof, mutation check, regression and provider/consumer interoperability.
- **REVIEW:** independent verifier for cross-repo or high-risk claims; no self-certified device behavior.
- **INTEGRATE:** integration owner approves PR and reconciles changed branch tips.
- **RELEASE:** only with device-specific rollback and explicit owner permission.

## Honest labels
Status is PASS / FAIL / BLOCKED / NOT_RUN. Evidence level is PROVEN_CODE, TESTED_OFFLINE, COMPILED, MEASURED_DEVICE, INFERRED, PROPOSED, UNKNOWN or NOT_RUN. PASS on a code inspection is not a claim of runtime passing; the exact command/result still matters. Synthetic fixture never equals device measurement. Baseline stability is not release acceptance.

## Deliverables per bounded task
Work order includes requested result, access boundary, owner, allowed/forbidden actions, exact dependency SHAs, executable acceptance conditions and failing baseline. Receipt includes source/branch/SHA, test command, exit code, artifacts and SHA-256, contradictions, blocked dependencies and next action. Link source-to-result, not just narrative to narrative.

## Privacy / release policy
The default is NO copying of private source, raw HAR traffic, authentication tokens, TV IPs, account lists, internal logs or private-repository paths to public artifacts. A public fixture must be specifically approved, independently checked for secrets and versioned. A public repo receives interface information needed to interoperate, not private project history.

## Verification command
Run `python3 scripts/agent_receipt.py self-test` and `python3 scripts/agent_receipt.py snapshot --executor <arena|local|chatgpt|ci>`. Store scoped receipts under the owning repo's existing evidence location; do not invent a duplicate evidence database.
