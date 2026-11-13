# Luma Code Review Checklist — Fast Scan + PR Review

This checklist is used by all agents (cloud and local macOS) before pushing to
the Arena branch and by reviewers before approving PR #2. It mirrors the
5-gate CI pipeline so failures are caught locally before they waste CI minutes.

## Pre-Push Checklist (Run `./scripts/fast-scan.sh` First)

| # | Check | Command / Method | Pass Criterion |
|---|-------|-----------------|----------------|
| 1 | Working tree clean | `git status --porcelain` | No uncommitted changes |
| 2 | Sandbox static verify | `python3 scripts/sandbox_verify.py` | 0 errors |
| 3 | Import consistency | `./scripts/fast-scan.sh` | 0 import warnings |
| 4 | StackItem fields | All initializers include all 7 fields | No missing fields |
| 5 | Feature gating | `nuvio_lab` in Cargo.toml, cfg-gated in code | No silent runtime override |
| 6 | Format | `cargo fmt --all --check` (needs Rust) | 0 diffs |
| 7 | Compile | `cargo check --features nuvio,nuvio_lab` (needs Rust) | 0 errors |
| 8 | Tests | `cargo test --all-features` (needs Rust) | All pass |
| 9 | Clippy | `cargo clippy --all-targets --all-features -- -D warnings` (needs Rust) | 0 warnings |
| 10 | CI pin compatibility | Code compiles on Rust 1.93.0 | No `if let` guards, no newer-Rust-only syntax |

## PR-Specific Checklist (Nuvio Lab Integration)

| # | Check | Location | Pass Criterion |
|---|-------|----------|----------------|
| A | Production app ID unchanged | `src/platform.rs` | `NUVIO_APP_ID == "space.nuvio.webos"` |
| B | Lab app ID distinct | `src/platform.rs` | `NUVIO_LAB_APP_ID == "space.nuvio.lab"` |
| C | Lab ID valid per `valid_app_id()` | `src/model.rs` | Passes validation |
| D | No silent runtime override | `src/platform.rs` | `nuvio_app_id(true)` falls back to production if feature missing |
| E | Test target visible in build metadata | `Cargo.toml` | `nuvio_lab = []` feature declared |
| F | Test artifacts distinguishable | `src/main.rs` | PID-scoped temp fixture path |
| G | No extra media launcher | `src/main.rs`, `src/state.rs` | No duplicate routing layer |
| H | Rollback safe | `Cargo.toml`, `src/platform.rs` | No production Nuvio modification needed |
| I | LCKV consumer read-only | `src/fast_kv.rs`, `src/nuvio.rs` | `read_bridge_cards` takes `&path`, no writes |
| J | Seqlock enforcement | `src/fast_kv.rs` | head == tail && even required |
| K | Empty bridge = valid empty, not synthetic | `src/nuvio.rs` | `bridge_items` returns `Some(vec![])` |

## Round 1-2 Lessons (Already Encountered — Do Not Reintroduce)

| # | Lesson | Fix Applied | File |
|---|--------|-------------|------|
| 1 | `"code-complete"` claimed but 17+49 compile errors | Fix all errors before claiming complete | All |
| 2 | `sender` field renamed to `requests` but constructor not updated | `sender` → `requests` in `Platform::new()` | `src/platform.rs` |
| 3 | `Request` enum missing `#[derive(Debug)]` for `payload_eq()` | Added `#[derive(Debug)]` | `src/platform.rs` |
| 4 | `Response` enum missing `#[derive(Debug)]` for test `panic!` | Added `#[derive(Debug)]` | `src/platform.rs`, `src/nuvio.rs` |
| 5 | `u8::is_ascii_digit` type mismatch (needs closure) | `|| !id.bytes().all(|b: u8| b.is_ascii_digit())` | `src/platform.rs` |
| 6 | `StackItem` missing 4 fields in initializer | Added `content_target`, `progress_permille`, `poster_url`, `still_url` | `src/main.rs` |
| 7 | `File::write_all` missing `use std::io::Write` | Added `Write` to imports | `src/app_artwork.rs` |
| 8 | `image::RgbaImage::from_vec` returns `Option`, not `Result` | `.ok()?` → `?` | `src/app_artwork.rs` |
| 9 | `draw_mesh(&mut self)` conflicts with immutable `self.batches` borrow | Reverted to `&self`, removed `flush_quad_batcher()` from body | `src/renderer.rs` |
| 10 | `path` moved into `textures.insert`, then used again | `path.clone()` before move | `src/renderer.rs` |
| 11 | `if let` guards experimental on Rust 1.93 | `matches!(opaque_frost(path), Some(_))` + `.expect()` | `src/renderer.rs` |
| 12 | `nuvio::Response` missing `#[derive(Debug)]` | Added `#[derive(Debug)]` | `src/nuvio.rs` |
| 13 | `mod nuvio` in tests shadows `crate::nuvio` | Explicit `use crate::nuvio::{Command, Service}` + `Response as NuvioResponse` | `src/tests.rs` |
| 14 | `tempfile` crate missing from dev-dependencies | Added `tempfile = "3"` to `[dev-dependencies]` | `Cargo.toml` |
| 15 | `rustfmt.toml` caused 141 fmt diffs | Deleted `rustfmt.toml` | Root |
| 16 | Motion test module private, functions non-existent | Made `pub(crate)`, removed non-existent calls | `src/motion.rs`, `src/main.rs` |
| 17 | `row_stack()` returns `usize` index, not `StackConfig` | `self.preferences.stacks[stack_idx].shape` | `src/state.rs` |
| 18 | Doc comments on match arms trigger unused_doc_comments | Converted to `//` plain comments | `src/platform.rs`, `src/state.rs`, `src/main.rs` |
| 19 | Unused `FastBridgeCard` import in nuvio.rs | Removed import | `src/nuvio.rs` |
| 20 | Unused `Response` import in tests.rs | Removed from top-level, added inside `mod nuvio` | `src/tests.rs` |

## CI Compatibility Notes

- **Rust 1.93.0 (CI pin)**: Too old for `if let` guards. `origin/main` also fails on 1.93 at `src/renderer.rs:1883`. Consider bumping CI to 1.96+ or rewriting guards.
- **Rust 1.96.0 (local stable)**: Compiles `origin/main` with 0 errors. Use this as the reference toolchain.
- **No Rust toolchain in cloud sandbox**: `static.rust-lang.org` and `sh.rustup.rs` are blocked. All `cargo` commands blocked locally.
- **Cross-environment**: Cloud agent writes code; local macOS agent runs `cargo` gates; GitHub Actions CI runs final validation.

## Fast Scan Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | All checks passed |
| 1 | One or more errors found — fix before push |
| 2 | Missing dependency (e.g., python3 not found) |
