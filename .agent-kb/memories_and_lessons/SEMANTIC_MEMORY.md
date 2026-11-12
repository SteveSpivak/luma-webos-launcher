# Semantic Memory — Architectural Laws & Non-Obvious Invariants

**Purpose**: Unwritten architectural laws discovered through code inspection,
compile-error forensics, and design review. Every agent must internalize these
before making changes. Append-only; corrections require a new entry referencing
this one.

---

## SM-01: Production App ID Is Sacred

**Statement**: `NUVIO_APP_ID = "space.nuvio.webos"` is never changed, never
overridden at runtime, and never used to launch from Luma in this repo.

**Evidence**: `src/platform.rs` line ~25: `pub const NUVIO_APP_ID: &str = "space.nuvio.webos";`

**Corollary**: Any code that sets `NUVIO_APP_ID` at runtime based on user input,
config, or environment variable violates this law.

---

## SM-02: Lab App ID Is Feature-Gated and Runtime-Optional

**Statement**: `NUVIO_LAB_APP_ID = "space.nuvio.lab"` exists only behind
`#[cfg(feature = "nuvio_lab")]`. `nuvio_app_id(lab: bool)` returns production
ID when `lab=false` or when the feature is not compiled.

**Evidence**: `src/platform.rs` `nuvio_app_id()` function — the `#[cfg(not(feature = "nuvio_lab"))]` branch returns `NUVIO_APP_ID` to prevent silent runtime override.

**Corollary**: A build without `nuvio_lab` can never produce `space.nuvio.lab`
launch parameters, even if `lab=true` is passed at runtime.

---

## SM-03: LCKV Consumer Is Read-Only

**Statement**: `read_bridge_cards(path, collection)` takes `&path`. The consumer
never writes to the bridge file. Writing is owned by the NuvioTV producer.

**Evidence**: `src/fast_kv.rs` — `read_bridge_cards` signature: `pub fn read_bridge_cards(path: &Path, collection: &str) -> io::Result<Vec<FastBridgeCard>>`.

**Corollary**: Any consumer-side `write_bridge_cards` call is a bug.

---

## SM-04: Seqlock Integrity Is Non-Negotiable

**Statement**: Reader accepts LCKV file only when `head_seq == tail_seq && head_seq % 2 == 0`. Odd seq or mismatch = torn write = rejected with `WouldBlock`.

**Evidence**: `src/fast_kv.rs` lines ~124-137: `if (seq_head & 1) == 1 || seq_head != seq_tail { return Err(...) }`.

**Corollary**: `seq=0` is valid (even, head==tail). `seq=1` is invalid.

---

## SM-05: Empty Bridge Is Valid Empty, Not Synthetic Fallback

**Statement**: A bridge file with 0 cards returns `Some(vec![])`. Synthetic
fixtures are only used when the bridge file is missing or unreadable (`None`).

**Evidence**: `src/nuvio.rs` `bridge_items()`: `Ok(cards) => cards` → `Some(cards)`; `Err(_) => return None`. Caller falls back to synthetic only on `None`.

**Corollary**: `tombstone_40` test asserts `read.len() == 0`, not synthetic content.

---

## SM-06: Focus Preservation During Nuvio Launch

**Statement**: `Target::NuvioLaunch` does not modify `state.focus`. Back out of
Nuvio returns to Luma with the same focus.

**Evidence**: `src/state.rs` `activate()` match arm for `Target::NuvioLaunch` returns `Effect::NuvioLaunch` without changing `self.focus`. `src/main.rs` `Effect::NuvioLaunch` handler sets `state.launching = true` but does not touch focus.

**Corollary**: Any code that changes focus during Nuvio launch violates this law.

---

## SM-07: No Duplicate Launches In-Flight

**Statement**: `!self.launching` guard prevents a second `Effect::NuvioLaunch`
while one is in progress.

**Evidence**: `src/state.rs` `Target::NuvioLaunch(ref content_target) if !self.launching` and `src/main.rs` `if !state.launching { state.launching = true; ... }`.

**Corollary**: Rapid double-click of a Nuvio card produces one launch, not two.

---

## SM-08: No Texture Clearing, No Freeze on FocusLost

**Statement**: `self.textures.clear()` is forbidden. Renderer continues when
window still visible after `FocusLost`.

**Evidence**: Council verdict. No code in `src/renderer.rs` calls `clear()` on textures.

**Corollary**: Any VRAM-clearing or freeze-on-focus-lost code is a regression.

---

## SM-09: No Experimental VRAM / Decoder / Memory Features

**Statement**: No experimental VRAM clearing, fixed decoder-drain delays, or new
memory governor may be added.

**Evidence**: Council verdict. Code search confirms none exist.

**Corollary**: Performance work must use existing mechanisms, not new governors.

---

## SM-10: `#[derive(Debug)]` Required on Request and Response Enums

**Statement**: `platform::Request` and `platform::Response` need `#[derive(Debug)]`
for `payload_eq()` format comparison and test `panic!("{response:?}")`.

**Evidence**: Round 1-2 compile errors E0277 on both enums.

**Corollary**: Any new enum variant added to `Request` or `Response` automatically gets Debug via derive.

---

## SM-11: `u8::is_ascii_digit` Needs Closure on Rust 1.93

**Statement**: `id.bytes().all(u8::is_ascii_digit)` fails on Rust 1.93 because
`u8::is_ascii_digit` is `fn(&u8) -> bool` but `Iterator::all` expects
`fn(u8) -> bool`. Must use `|b: u8| b.is_ascii_digit()`.

**Evidence**: Round 1-2 compile error E0631 on `src/platform.rs:287`.

**Corollary**: All `.all()` calls on byte iterators need explicit closure form.

---

## SM-12: `mod nuvio` in Tests Shadows `crate::nuvio`

**Statement**: A `mod nuvio` inside `tests.rs` creates a namespace where `nuvio::Service`
resolves to `crate::tests::nuvio::Service` (doesn't exist), not `crate::nuvio::Service`.

**Evidence**: Round 2 compile errors E0433 on `nuvio::Service`, `nuvio::Command`.

**Corollary**: Inside `mod nuvio` in tests, use `use crate::nuvio::{Command, Service}` and `use crate::nuvio::Response as NuvioResponse` to disambiguate.

---

## SM-13: `rustfmt.toml` Causes 141 Fmt Diffs

**Statement**: The project's `rustfmt.toml` with `style_edition = "2021"`,
`max_width = 100` conflicts with default `cargo fmt` behavior. Delete it and
run `cargo fmt --all` instead.

**Evidence**: Round 1-2 fmt check: 141 diffs with `rustfmt.toml`, 0 after deletion + `cargo fmt --all`.

**Corollary**: Do not add `rustfmt.toml` back. If formatting rules are needed,
configure via `.rustfmt.toml` (different file) or rustfmt command-line flags.

---

## SM-14: CI Pin (1.93.0) < Local Stable (1.96.0)

**Statement**: `origin/main` compiles on Rust 1.96.0 with 0 errors but fails on
1.93.0 due to `if let` guards (experimental feature). CI uses `dtolnay/rust-toolchain@1.93.0`.

**Evidence**: Round 2 `app-check-1.93.log` shows E0658 at `src/renderer.rs:2033`.

**Corollary**: Either bump CI toolchain to 1.96+ or rewrite all `if let` guards
as `matches!` + nested `if`. Prefer bumping CI to match local development.

---

## SM-15: `row_stack()` Returns `usize` Index, Not `StackConfig`

**Statement**: `crate::stacks::row_stack(state, row)` returns `Option<usize>`
(the index into `preferences.stacks`), not a `StackConfig` reference. Callers
must index: `self.preferences.stacks[idx].shape`.

**Evidence**: Round 1-2 errors E0610 at `src/state.rs:2208,2226`: `usize` has no
field `shape`.

**Corollary**: All callers of `row_stack()` must treat the result as an index.

---

## SM-16: Doc Comments on Match Arms Trigger Warnings

**Statement**: `///` doc comments on `match` arms are not processed by rustdoc
and trigger `unused_doc_comments` warnings, which fail `clippy -D warnings`.

**Evidence**: Round 2 clippy warnings on `src/platform.rs:198`, `src/state.rs:4518`, `src/main.rs:272`.

**Corollary**: Use `//` plain comments on match arms, not `///` doc comments.

---

## SM-17: `image::RgbaImage::from_vec` Returns `Option`, Not `Result`

**Statement**: `from_vec()` returns `Option<RgbaImage>`, so `.ok()?` is a type
error. Use `?` directly on the `Option`.

**Evidence**: Round 1-2 errors on `src/app_artwork.rs:157,171`.

**Corollary**: Replace `.ok()?` with `?` on `from_vec()` calls.

---

## SM-18: `File::write_all` Requires `use std::io::Write`

**Statement**: `write_all` is a trait method on `std::io::Write`. It must be
imported to be called on `File`.

**Evidence**: Round 1-2 errors E0599 on `src/app_artwork.rs:96,97`.

**Corollary**: Always `use std::io::Write` when calling `write_all`, `write_all_at`, etc.

---

## SM-19: `tempfile` Is a Dev-Dependency, Not a Regular Dependency

**Statement**: `tempfile` crate is used only in `#[cfg(test)]` code in
`src/fast_kv.rs`. It must be in `[dev-dependencies]`, not `[dependencies]`.

**Evidence**: Round 1-2 errors E0433: `cannot find module or crate tempfile`.

**Corollary**: Add test-only crates to `[dev-dependencies]` in `Cargo.toml`.

---

## SM-20: StackItem Has 7 Fields; All Must Be Initialized

**Statement**: `StackItem` has fields: `title`, `poster`, `id`, `content_target`,
`progress_permille`, `poster_url`, `still_url`. All 7 must be provided in
struct initializers (no `Default` derive).

**Evidence**: Round 1-2 errors E0063 on `src/main.rs:2092` and `src/tests.rs`.

**Corollary**: Use `..Default::default()` only if `Default` is derived, or list
all fields explicitly. `StackItem` does not derive `Default`.
