# PR Fast-Scan Review Guide

**Purpose**: Review any PR or branch in under 5 minutes using deterministic
checks before reading any code. Designed for PR #2 review on
`arena/5fe14abb-luma-webos-launcher`.

---

## Phase 1: Metadata Check (< 30 seconds)

| Check | Command | Pass Criterion |
|-------|---------|----------------|
| Branch | `git rev-parse --abbrev-ref HEAD` | `arena/5fe14abb-luma-webos-launcher` |
| Base | `git merge-base main HEAD` | Should be `40994fc` (origin/main) |
| Working tree | `git status --porcelain` | Clean (or only intentional changes) |
| PR open | `gh pr list --repo SteveSpivak/luma-webos-launcher` | PR #2 exists, status: open |

---

## Phase 2: Fast Scan (< 30 seconds, no Rust needed)

Run from repo root:

```bash
./scripts/fast-scan.sh
```

| Gate | Command | Pass Criterion |
|------|---------|----------------|
| Sandbox verify | `python3 scripts/sandbox_verify.py` | 0 errors |
| Import consistency | `./scripts/fast-scan.sh` | 0 import warnings |
| StackItem fields | All initializers have 7 fields | No missing fields |
| Feature gating | `nuvio_lab` in Cargo.toml | Declared and cfg-gated |

**If fast scan fails**: Do not read code. Ask the author to fix and re-push.

---

## Phase 3: Full Rust Gates (< 5 minutes, needs Rust toolchain)

Run on local macOS agent or GitHub Actions CI:

```bash
cargo fmt --all --check
cargo check --features nuvio,nuvio_lab
cargo test --no-run --all-features
cargo clippy --all-targets --all-features -- -D warnings
cargo test --all-features
```

| Gate | Command | Pass Criterion |
|------|---------|----------------|
| Format | `cargo fmt --all --check` | 0 diffs |
| Check | `cargo check --features nuvio,nuvio_lab` | 0 errors |
| Test build | `cargo test --no-run --all-features` | 0 errors |
| Clippy | `cargo clippy --all-targets --all-features -- -D warnings` | 0 warnings |
| Test run | `cargo test --all-features` | All tests pass |

**If any gate fails**: Do not approve. Request fix + re-scan.

---

## Phase 4: Semantic Review (< 5 minutes, read code)

Only after all gates pass. Check these specific invariants:

| Invariant | Where to Look | Pass Criterion |
|-----------|---------------|----------------|
| Production app ID unchanged | `src/platform.rs` | `NUVIO_APP_ID == "space.nuvio.webos"` |
| Lab app ID distinct | `src/platform.rs` | `NUVIO_LAB_APP_ID == "space.nuvio.lab"` |
| Lab ID valid | `src/model.rs` | `valid_app_id("space.nuvio.lab")` true |
| No silent override | `src/platform.rs` | `nuvio_app_id(true)` falls back to production |
| Read-only consumer | `src/fast_kv.rs` | `read_bridge_cards` takes `&path` |
| Seqlock enforcement | `src/fast_kv.rs` | `head == tail && even` required |
| Empty bridge valid | `src/nuvio.rs` | `bridge_items` returns `Some(vec![])` |
| Focus preserved | `src/state.rs` | `Target::NuvioLaunch` doesn't change focus |
| No duplicate launch | `src/main.rs` | `!self.launching` guard present |
| No VRAM clearing | `src/renderer.rs` | No `self.textures.clear()` |
| No `if let` guards | `src/renderer.rs` | No `if let ... =>` match guards |

---

## Phase 5: PR-Specific Checks for #2

| Check | Location | Pass Criterion |
|-------|----------|----------------|
| `nuvio_lab` feature | `Cargo.toml` | `nuvio_lab = []` declared |
| Lab app ID const | `src/platform.rs` | `#[cfg(feature = "nuvio_lab")] NUVIO_LAB_APP_ID` |
| Lab launch params | `src/platform.rs` | `nuvio_launch_params_lab()` cfg-gated |
| Lab tests | `src/tests.rs` | 4 lab app ID tests present |
| LCKV tests | `src/fast_kv.rs` | 14 unit tests present |
| Lab command | `src/main.rs` | `lab_command()` writes to PID-scoped temp fixture |

---

## Fast-Scan Decision Matrix

| Fast Scan Result | Rust Gates Result | Decision |
|-----------------|-------------------|----------|
| Pass | Pass | ✅ Approve |
| Pass | Fail | ❌ Request fix + re-scan |
| Fail | (any) | ❌ Request fix + re-scan (don't waste Rust minutes) |
| (skip) | Pass | ⚠️ Acceptable if cloud agent lacks python3 |

---

## Rejection Template (Copy/Paste)

```
PR #2 cannot be approved yet.

Fast scan result: [PASS/FAIL] — [details]
Rust gates result: [PASS/FAIL/not run] — [details]

Specific issues:
- [file:line] — [error] — [fix needed]

Please:
1. Fix the errors above
2. Run ./scripts/fast-scan.sh
3. Run cargo fmt/check/test/clippy on local macOS or wait for GitHub Actions CI
4. Re-push and request re-review

References:
- .agent-kb/scripts/code-review-checklist.md
- .agent-kb/memories_and_lessons/EPISODIC_LESSONS.md
```
