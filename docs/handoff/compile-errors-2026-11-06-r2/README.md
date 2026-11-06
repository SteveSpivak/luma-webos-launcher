# Round 2: compile errors on `ac10fe8` (2026-11-06)

**Bottom line: `ac10fe8` fixed most of round 1, but the branch still does not build.
App: 3 errors (stable), plus `if let` guards on 1.93. Tests: 13. Clippy: 15. fmt: 43 diffs.
Three of the app errors were introduced by the round-1 fixes.**

Measured by the owner's local Mac agent (stable `rustc 1.96.0`, CI pin `1.93.0`). Logs here, paths and IPs redacted.

## Gate results (MEASURED)
| Gate | Command | Round 1 (`599edf7`) | Round 2 (`ac10fe8`) | Log |
|---|---|---|---|---|
| App, stable | `cargo check --features nuvio,nuvio_lab` | 17 | **3** | `app-check-stable.log` |
| App, CI pin | `cargo +1.93.0 check --features nuvio,nuvio_lab` | fails | fails (`if let` guards) | `app-check-1.93.log` |
| Format | `cargo +1.93.0 fmt --all --check` | 141 diffs | 43 diffs | `fmt-check-1.93.log` |
| Tests build | `cargo test --no-run --all-features` | 49 | 13 | `test-build-stable.log` |
| Clippy | `cargo clippy --all-targets --all-features -- -D warnings` | 51 | 15 | `clippy-stable.log` |

## App errors
| File:line | Error | Hint |
|---|---|---|
| `src/renderer.rs:1469` | E0382 borrow of moved value `path` | Round-1 fix moved `path` into an insert, then uses it again. Clone before the move, or reorder |
| `src/renderer.rs:2335`, `:2349` | E0502 cannot borrow `*self` as mutable while `for batch in &self.batches` (line 2233) holds it | Caused by `draw_mesh(&self)` → `&mut self`. Revert that and fix the original borrow differently, or take/iterate indices |
| `src/renderer.rs:2033` (+3 more) | E0658 "`if let` guards are experimental" on 1.93.0 | Same as main `40994fc`. Bump CI toolchain, or rewrite as nested `if let` |

## Test / clippy errors
- `nuvio::Response` needs `#[derive(Debug)]` (`src/nuvio.rs:196,210,225`; `src/tests.rs:3651,3672,3686`). Round 1 added Debug to `platform::Response`, not `nuvio::Response`.
- `nuvio::Response::Launched` does not exist (`src/tests.rs:3588,3603`). Check the real variant name in `src/nuvio.rs`.
- Clippy: unused import `Response` (`src/tests.rs:8`), unused variable `full` (`src/renderer.rs:1513`).

## Format
`rustfmt.toml` is deleted, but `cargo fmt --all` was never run: 43 diffs remain. Run it on the CI toolchain.

## Ask
You have no Rust toolchain, so each round is blind. Please fix the list above, run `cargo fmt --all`,
and push. The local agent re-runs all 5 gates in about 3 minutes.
