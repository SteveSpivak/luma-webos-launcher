# Episodic Lessons — Failures, Fixes, and Falsified Assumptions

**Purpose**: Every entry records a real failure encountered during this
integration, the root cause, the fix, and how to detect it earlier next time.
Append-only. Each entry is falsifiable: it references a commit SHA and a
measurable symptom.

---

## EL-001: "Code-Complete" Claim Was False

**Date**: 2026-11-06
**Commit**: `599edf7` (PR head before round-1 fixes)
**Symptom**: Cloud agent claimed implementation was "code-complete." Local macOS
agent measured 17 app + 49 test + 51 clippy compile errors on untouched checkout.
**Root Cause**: No Rust toolchain in cloud sandbox; code was written and
committed without `cargo check` / `cargo test` / `cargo clippy` verification.
**Fix**: Round 1 fixes (commit `a656c8c`) resolved 17 app errors; round 2
fixes (commit `e956532`) resolved remaining 3 app + 13 test + 15 clippy errors.
**Detection**: `./scripts/fast-scan.sh` + local macOS `cargo check` before any
"code-complete" claim.
**Falsification**: Run `cargo check --features nuvio,nuvio_lab` — must return 0 errors.

---

## EL-002: `sender` Field Renamed to `requests` but Constructor Not Updated

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `error[E0425]: cannot find value sender in this scope` at
`src/platform.rs:239`.
**Root Cause**: `Platform` struct field renamed from `sender` to `requests` but
`Self { sender, receiver, webos }` constructor still referenced `sender`.
**Fix**: Changed `sender` to `requests` in constructor (commit `a656c8c`).
**Detection**: `python3 scripts/sandbox_verify.py` catches unbalanced braces
but not field-name mismatches; `cargo check` catches this.
**Falsification**: `cargo check` must pass with 0 errors on `platform.rs`.

---

## EL-003: Missing `#[derive(Debug)]` on `Request` and `Response`

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `error[E0277]: platform::Request doesn't implement std::fmt::Debug`
at `src/platform.rs:70` (two occurrences). Same for `Response` in tests.
**Root Cause**: `payload_eq()` uses `format!("{self:?}")` which requires `Debug`.
Test `panic!("{response:?}")` also requires `Debug`.
**Fix**: Added `#[derive(Debug)]` to both enums (commit `a656c8c` for
`platform.rs`, `e956532` for `nuvio.rs`).
**Detection**: `cargo check` or `cargo clippy -D warnings`.
**Falsification**: `cargo clippy --all-targets --all-features -- -D warnings`
must pass with 0 warnings.

---

## EL-004: `u8::is_ascii_digit` Type Mismatch on Rust 1.93

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `error[E0631]: type mismatch in function arguments` at
`src/platform.rs:287`: `id.bytes().all(u8::is_ascii_digit)`.
**Root Cause**: `u8::is_ascii_digit` is `fn(&u8) -> bool` but
`Iterator::all` expects `fn(u8) -> bool`. Rust 1.96 allows method reference
coercion; 1.93 does not.
**Fix**: Changed to `|| !id.bytes().all(|b: u8| b.is_ascii_digit())`
(commit `a656c8c`).
**Detection**: `cargo +1.93.0 check` or `cargo check` on any Rust version.
**Falsification**: Compile on Rust 1.93.0 must succeed.

---

## EL-005: `StackItem` Missing 4 Fields in Initializer

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `error[E0063]: missing fields content_target, poster_url,
progress_permille and 1 other field in initializer of StackItem` at
`src/main.rs:2092`.
**Root Cause**: `StackItem` gained 4 new fields (`content_target`,
`progress_permille`, `poster_url`, `still_url`) but the debug mockup
initializer in `main.rs` only provided `title`, `id`, `poster`.
**Fix**: Added all 4 missing fields with default values (commit `a656c8c`).
**Detection**: `cargo check` on `main.rs`.
**Falsification**: `cargo check` must pass with 0 errors on `main.rs`.

---

## EL-006: `File::write_all` Missing `use std::io::Write`

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `error[E0599]: no method named write_all found for struct File` at
`src/app_artwork.rs:96,97`.
**Root Cause**: `write_all` is a trait method on `std::io::Write`; import was
missing.
**Fix**: Added `Write` to `io::{Cursor, Read, Write}` (commit `a656c8c`).
**Detection**: `cargo check` on `app_artwork.rs`.
**Falsification**: `cargo check` must pass with 0 errors on `app_artwork.rs`.

---

## EL-007: `image::RgbaImage::from_vec` Returns `Option`, Not `Result`

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `error[E0599]: no method named ok found for enum Option<T>` at
`src/app_artwork.rs:157,171`.
**Root Cause**: `.ok()?` was called on the `Option` returned by `from_vec()`,
but `Option` has no `.ok()` method.
**Fix**: Changed `.ok()?` to `?` (commit `a656c8c`).
**Detection**: `cargo check` on `app_artwork.rs`.
**Falsification**: `cargo check` must pass with 0 errors on `app_artwork.rs`.

---

## EL-008: `draw_mesh(&mut self)` Borrow Conflict with `self.batches`

**Date**: 2026-11-06
**Commit**: `a656c8c` (round 1 fix)
**Symptom**: `error[E0502]: cannot borrow *self as mutable because it is also
borrowed as immutable` at `src/renderer.rs:2335,2349`.
**Root Cause**: Round 1 changed `draw_mesh(&self)` to `draw_mesh(&mut self)` to
call `flush_quad_batcher()`. But `draw_mesh` is called inside a loop iterating
`&self.batches`, creating an immutable borrow conflict.
**Fix**: Reverted to `draw_mesh(&self)` and removed `flush_quad_batcher()` call
from `draw_mesh` body. `flush_quad_batcher()` is still called at line 2073 in
the render loop (commit `e956532`).
**Detection**: `cargo check` on `renderer.rs`.
**Falsification**: `cargo check` must pass with 0 errors on `renderer.rs`.

---

## EL-009: `path` Moved Before Reuse

**Date**: 2026-11-06
**Commit**: `a656c8c` (round 1 fix)
**Symptom**: `error[E0382]: borrow of moved value: path` at
`src/renderer.rs:1469`.
**Root Cause**: Round 1 changed `&path` to `path.clone()` for
`apply_still_side_effects`, but `path` was then moved into
`textures.insert(path, ...)` and reused in `format!("{path}#frost")`.
**Fix**: Changed to `textures.insert(path.clone(), ...)` (commit `e956532`).
**Detection**: `cargo check` on `renderer.rs`.
**Falsification**: `cargo check` must pass with 0 errors on `renderer.rs`.

---

## EL-010: `if let` Guards Experimental on Rust 1.93

**Date**: 2026-11-06
**Commit**: `origin/main` (pre-existing) and `599edf7`
**Symptom**: `error[E0658]: if let guards are experimental` at
`src/renderer.rs:2033`.
**Root Cause**: `if let Some(source) = opaque_frost(path) =>` guard syntax is
experimental and not stable until Rust 1.96+. CI pin is 1.93.0.
**Fix**: Changed to `matches!(opaque_frost(path), Some(_))` + `let source =
opaque_frost(path).expect(...)` (commit `e956532`).
**Detection**: `cargo +1.93.0 check`.
**Falsification**: Compile on Rust 1.93.0 must succeed. Alternatively, bump CI
toolchain to 1.96+.

---

## EL-011: `nuvio::Response` Missing `#[derive(Debug)]`

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `error[E0277]: nuvio::Response doesn't implement std::fmt::Debug`
at `src/nuvio.rs:196,210,225` and `src/tests.rs:3651,3672,3686`.
**Root Cause**: Round 1 added `#[derive(Debug)]` to `platform::Response` but
not `nuvio::Response`. Tests use `{response:?}` on `nuvio::Response`.
**Fix**: Added `#[derive(Debug)]` to `nuvio::Response` (commit `e956532`).
**Detection**: `cargo check` or `cargo clippy -D warnings`.
**Falsification**: `cargo clippy --all-targets --all-features -- -D warnings`
must pass with 0 warnings.

---

## EL-012: `mod nuvio` in Tests Shadows `crate::nuvio`

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `error[E0433]: cannot find Service in nuvio` at `src/tests.rs:3640`.
**Root Cause**: `mod nuvio` inside `tests.rs` creates a nested module.
`nuvio::Service` resolves to `crate::tests::nuvio::Service`, not
`crate::nuvio::Service`.
**Fix**: Added `use crate::nuvio::{Command, Service}` and
`use crate::nuvio::Response as NuvioResponse` inside `mod nuvio`
(commit `e956532`). Also added `use crate::platform::Response` for
`Response::Launched`.
**Detection**: `cargo test --no-run --all-features`.
**Falsification**: `cargo test --no-run --all-features` must compile with 0 errors.

---

## EL-013: `tempfile` Crate Missing from Dev-Dependencies

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `error[E0433]: cannot find module or crate tempfile` at 10 sites
in `src/fast_kv.rs`.
**Root Cause**: `tempfile` used only in `#[cfg(test)]` code but not declared
in `[dev-dependencies]`.
**Fix**: Added `tempfile = "3"` to `[dev-dependencies]` in `Cargo.toml`
(commit `a656c8c`).
**Detection**: `cargo test --no-run --all-features`.
**Falsification**: `cargo test --no-run --all-features` must compile with 0 errors.

---

## EL-014: `rustfmt.toml` Causes 141 Fmt Diffs

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `cargo +1.93.0 fmt --all --check` reports 141 differences.
**Root Cause**: `rustfmt.toml` with `style_edition = "2021"`, `max_width = 100`
conflicts with default `cargo fmt` behavior.
**Fix**: Deleted `rustfmt.toml` (commit `a656c8c`). Run `cargo fmt --all` to
normalize, then `cargo fmt --all --check` passes.
**Detection**: `cargo fmt --all --check`.
**Falsification**: `cargo fmt --all --check` must report 0 diffs.

---

## EL-015: Motion Test Module Private, Functions Non-Existent

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `error[E0425]: cannot find function test_spring1d_settles_to_rest
in crate::motion::tests` at `src/main.rs:1842`. `error[E0603]: module tests is
private`.
**Root Cause**: `main.rs` `lab_command("motion")` called test functions that
don't exist in `motion::tests`, and the module was `mod tests` (private) not
`pub(crate) mod tests`.
**Fix**: Changed `mod tests` to `pub(crate) mod tests` and replaced the
non-existent function calls with a comment (commit `a656c8c`).
**Detection**: `cargo test --no-run --all-features`.
**Falsification**: `cargo test --no-run --all-features` must compile with 0 errors.

---

## EL-016: `row_stack()` Returns `usize` Index, Not `StackConfig`

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `error[E0610]: usize is a primitive type and therefore doesn't have
fields` at `src/state.rs:2208,2226`.
**Root Cause**: `crate::stacks::row_stack()` returns `Option<usize>` (index
into `preferences.stacks`), but code treated it as a `StackConfig` and
accessed `.shape`.
**Fix**: Changed to `self.preferences.stacks[stack_idx].shape` (commit
`a656c8c`).
**Detection**: `cargo check` on `state.rs`.
**Falsification**: `cargo check` must pass with 0 errors on `state.rs`.

---

## EL-017: Doc Comments on Match Arms Trigger Unused Doc Comments

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `warning: unused doc comment` at `src/platform.rs:198`,
`src/state.rs:4518`, `src/main.rs:272`.
**Root Cause**: `///` doc comments on `match` arms are not processed by rustdoc.
**Fix**: Converted to `//` plain comments (commit `a656c8c`).
**Detection**: `cargo clippy -D warnings`.
**Falsification**: `cargo clippy --all-targets --all-features -- -D warnings`
must pass with 0 warnings.

---

## EL-018: Unused `FastBridgeCard` Import in nuvio.rs

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `warning: unused import: FastBridgeCard` at `src/nuvio.rs:22`.
**Root Cause**: Import was added but `FastBridgeCard` is not referenced in
`nuvio.rs` (only in tests).
**Fix**: Removed `FastBridgeCard` from the import (commit `a656c8c`).
**Detection**: `cargo clippy -D warnings`.
**Falsification**: `cargo clippy --all-targets --all-features -- -D warnings`
must pass with 0 warnings.

---

## EL-019: Unused `Response` Import in tests.rs

**Date**: 2026-11-06
**Commit**: `599edf7`
**Symptom**: `warning: unused import: Response` at `src/tests.rs:8`.
**Root Cause**: `Response` imported from `crate::platform` but not used at
top level; needed inside `mod nuvio` instead.
**Fix**: Removed from top-level import, added `use crate::platform::Response`
inside `mod nuvio` (commit `e956532`).
**Detection**: `cargo clippy -D warnings`.
**Falsification**: `cargo clippy --all-targets --all-features -- -D warnings`
must pass with 0 warnings.

---

## EL-020: CI Toolchain Too Old for `if let` Guards

**Date**: 2026-11-06
**Commit**: `origin/main` (pre-existing)
**Symptom**: `origin/main` compiles on Rust 1.96.0 (0 errors) but fails on
1.93.0 with E0658 `if let guards are experimental`.
**Root Cause**: CI uses `dtolnay/rust-toolchain@1.93.0` which is older than
local stable 1.96.0.
**Fix**: Either bump CI to 1.96+ or rewrite all `if let` guards as `matches!`.
**Detection**: `cargo +1.93.0 check` on `origin/main`.
**Falsification**: `cargo +1.93.0 check` must pass on `origin/main` without
errors. If not, bump CI toolchain.

---

## Detection Checklist for Future Changes

Before any agent claims a fix is complete, verify:

- [ ] `cargo check --features nuvio,nuvio_lab` = 0 errors (needs Rust)
- [ ] `cargo test --no-run --all-features` = 0 errors (needs Rust)
- [ ] `cargo clippy --all-targets --all-features -- -D warnings` = 0 warnings (needs Rust)
- [ ] `cargo fmt --all --check` = 0 diffs (needs Rust)
- [ ] `python3 scripts/sandbox_verify.py` = 0 errors (no Rust needed)
- [ ] `./scripts/fast-scan.sh` = exit 0

If no Rust toolchain is available (cloud sandbox), the last two are the
maximum verification possible. The local macOS agent or GitHub Actions CI
must run the full 5-gate validation.
