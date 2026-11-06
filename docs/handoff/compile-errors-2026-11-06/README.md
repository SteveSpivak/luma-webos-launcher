# Compile errors on `arena/5fe14abb-luma-webos-launcher` @ `599edf7` (2026-11-06)

**Bottom line: this branch does not build. The app binary has 17 compile errors,
the test build 49, clippy (all targets, all features) 51. CI also fails `cargo fmt --check`
(141 diffs). No IPK can be built until these are fixed.**

Found by the owner's local Mac agent on an untouched checkout of `599edf7`.
Logs in this folder (home paths and IPs redacted).

## Toolchains
- Stable: `rustc 1.96.0`
- CI pin: `1.93.0` (`dtolnay/rust-toolchain@1.93.0`)
- Note: `origin/main` (`40994fc`) compiles on stable with 0 errors, but fails on
  1.93.0: "`if let` guards are experimental" at `src/renderer.rs:1883`.
  The CI pin looks too old for main (INFERRED). Consider bumping it.

## Gate results (MEASURED)
| Gate | Command | Result | Log |
|---|---|---|---|
| App build | `cargo check` | 17 errors | `app-check-stable.log` |
| Format | `cargo +1.93.0 fmt --all --check` | 141 diffs | `fmt-check-1.93.log` |
| Tests build | `cargo test --no-run --all-features` | 49 errors | `test-build-stable.log` |
| Clippy | `cargo clippy --all-targets --all-features` | 51 errors | `clippy-all-targets-stable.log` |

Same 17 app errors with `--features nuvio` and `--features nuvio,nuvio_lab`.

## App errors (fix these first)
| File:line | Error |
|---|---|
| `src/platform.rs:70` | `platform::Request` doesn't implement `Debug` (x2) |
| `src/platform.rs:239` | struct `Platform` has no field named `sender`; `sender` not found in scope |
| `src/platform.rs:287` | E0631 type mismatch in function arguments |
| `src/main.rs:2092` | `StackItem` initializer missing `content_target`, `poster_url`, `progress_permille` and 1 other |
| `src/app_artwork.rs:96,97` | no method `write_all` on `File` (missing `use std::io::Write`?) |
| `src/app_artwork.rs:157,171` | no method `ok` on `Option<T>` |
| `src/renderer.rs:1457,1460,1517` | mismatched types |
| `src/renderer.rs:2533` | cannot borrow `*self` as mutable behind `&` |
| `src/state.rs:2208,2226` | `usize` is a primitive type and doesn't have fields |

Pattern (INFERRED): looks like a merge of main into this branch that kept old call
sites against new types (`StackItem`, `Platform`, `Response`).

## Test-only errors
- `tempfile` crate missing: `src/fast_kv.rs` (about 10 sites). Add it to `[dev-dependencies]`.
- `module tests is private`: `src/main.rs:1842-1844`.
- `platform::Response::Items` not found: `src/tests.rs:3645,3666,3667,3682`.
- Missing `nuvio::Service` / `Command` and motion test functions (see log).

## Format
- The branch adds `rustfmt.toml` with `style_edition = "2021"`, `max_width = 100`.
  CI's `cargo fmt --check` then reports 141 diffs.
- MEASURED locally: deleting `rustfmt.toml` and running `cargo +1.93.0 fmt --all`
  makes the check pass (changes 12 files). Not pushed here; your call.

## Done when
1. `cargo check --features nuvio,nuvio_lab` = 0 errors.
2. `cargo test --all-features` builds and passes.
3. `cargo clippy --all-targets --all-features -- -D warnings` clean.
4. `cargo fmt --all --check` clean on the CI toolchain.
5. Then the webOS IPK build (`nuvio_lab` feature, app id `space.nuvio.lab`).
