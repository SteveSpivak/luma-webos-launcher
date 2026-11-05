# Measurement Protocol — Nuvio Integration

## 1. Status: BLOCKED (no toolchain)

This sandbox has **no Rust toolchain** (`cargo`/`rustc`/`rustfmt` absent) and **no pnpm**. The following commands cannot be executed here. They are documented as the exact commands to run when a Rust toolchain is available. No measurements are claimed.

## 2. Gate 1 validation commands

When a Rust toolchain (rust 1.93.0 per `.github/workflows/ci.yml`) is available:

```bash
# Formatting
cargo fmt --all -- --check

# Lint (CI runs with -D warnings)
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings

# Unit tests (includes nuvio feature-gated tests)
cargo test --locked --workspace --all-features

# Default-feature build (must be unchanged by Nuvio)
cargo build --locked

# Nuvio feature build (must compile)
cargo build --locked --features nuvio
```

### Expected results

| Command | Expected exit code | What pass looks like |
|---|---|---|
| `cargo fmt --all -- --check` | 0 | No formatting diffs |
| `cargo clippy -D warnings --all-features` | 0 | No clippy warnings, including no `dead_code` for `NUVIO_APP_ID`/`NUVIO_NOT_INSTALLED` |
| `cargo test --workspace --all-features` | 0 | All tests pass, including 8 nuvio tests |
| `cargo build --locked` (default) | 0 | Default build compiles unchanged |
| `cargo build --locked --features nuvio` | 0 | Nuvio feature compiles |

## 3. Test inventory (source-level)

### Phase 1 unit tests (`src/tests.rs`, `#[cfg(feature = "nuvio")]`)

| Test | What it verifies | Negative coverage |
|---|---|---|
| `nuvio_target_validates_movie_and_series_identifiers` | `nuvio://tmdb/movie/603`, `nuvio://tmdb/tv/129973`, `nuvio://tmdb/tv/1` accepted | — |
| `nuvio_target_rejects_malformed_targets` | 11 invalid targets rejected | Empty, missing ID, non-numeric ID, trailing slash, wrong kind (`episode`), query string, wrong host (`other`), uppercase, trailing space, missing scheme, HTTPS URL |
| `nuvio_app_id_is_fixed_and_valid` | `NUVIO_APP_ID == "space.nuvio.webos"`, passes `valid_app_id()` | — |
| `nuvio_launch_params_match_the_contract` | Payload equals `{"id": "space.nuvio.webos", "params": {"contentTarget": "nuvio://tmdb/movie/603"}}` | — |
| `nuvio_launch_routes_through_the_platform_worker` | `Platform::new(true)` + `Request::NuvioLaunch` → `Response::Launched(Err)` with ARM-only error | Desktop Luna unavailable error expected |
| `nuvio_invalid_target_is_rejected_before_reaching_tv_services` | Invalid target → `Err("Invalid Nuvio content target")` before any `call()` | No TV service reached |
| `nuvio_duplicate_launch_is_blocked_while_launching` | `state.launching == true` → `activate()` returns `[]` | Duplicate blocked |
| `nuvio_launch_keeps_focus_for_back_restoration` | `activate()` → focus unchanged | Focus preserved for Back |

### Negative test scenarios (documented, not all executable without toolchain)

| Scenario | Expected behavior | Test location |
|---|---|---|
| Malformed content target | `Err("Invalid Nuvio content target")`, no TV call | `nuvio_target_rejects_malformed_targets` |
| Missing Nuvio app | `state.notify("Nuvio isn't installed.")`, `launching = false` | Source inspection only (needs TV) |
| Duplicate launch while launching | `activate()` returns `[]`, no `platform.send()` | `nuvio_duplicate_launch_is_blocked_while_launching` |
| Desktop (no webOS) | `desktopPreview` notice, no Luna call | `nuvio_launch_routes_through_the_platform_worker` |
| Focus preservation | `state.focus` unchanged after `activate()` | `nuvio_launch_keeps_focus_for_back_restoration` |

## 4. What cannot be measured without a TV or native build

| Measurement | Why blocked |
|---|---|
| Cold/warm launch time | No native build, no TV |
| Focus-to-first-swap latency | No renderer execution |
| Frame pacing (p50/p95/p99) | No instrumentation, no TV |
| CPU/memory for artwork | No profiling build |
| Nuvio detail page correctness | Nuvio app owned by Nuvio, not Luma |
| Back button behavior on TV | Requires physical TV or simulator |
| `getAppInfo` preflight latency | Requires TV services |

## 5. Measurement receipt template

When a toolchain is available, record:

```
Command: cargo test --locked --workspace --all-features
Exit code: [RECORD]
Duration: [RECORD]
Tests passed: [RECORD]
Tests failed: [RECORD]
Nuvio tests passed: [RECORD] (expect 8)

Command: cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
Exit code: [RECORD]
Warnings: [RECORD] (expect 0)

Command: cargo fmt --all -- --check
Exit code: [RECORD]
Diffs: [RECORD] (expect none)

Command: cargo build --locked --features nuvio
Exit code: [RECORD]
```

**Rule:** Do not mark unexecuted device tests as PASS. Stop after two repeated failures.

## 6. CI evidence

The repository's `.github/workflows/ci.yml` runs:
- `pnpm format:check`
- `pnpm check` (clippy)
- `pnpm test` (cargo test --workspace --all-features)
- `xvfb-run pnpm test:smoke` (desktop rendering)
- `pnpm build` + `pnpm package` (cross-build for ARM webOS)

These provide the historical evidence baseline. Phase 1 changes must pass all of them when a toolchain is available.

## 7. Rollback verification

After rollback (`git revert 6dc1886 3031417` or `git reset --hard 40994fc`):

```bash
cargo build --locked        # default build unchanged
cargo test --locked         # all pre-existing tests pass
```

Exit code 0 for both confirms clean rollback.