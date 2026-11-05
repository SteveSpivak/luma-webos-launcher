# Bounded Next Implementation Step

## Current status

Phase 1 source is complete and committed on `arena/5fe14abb-luma-webos-launcher` (commit `6dc1886`), with draft PR #2 open. Gate 1 (native build + test verification) is **BLOCKED in this sandbox** — no Rust toolchain and no pnpm available locally. CI provides Rust 1.93 via `dtolnay/rust-toolchain@1.93.0`; results must be obtained from GitHub Actions.

## Step 1: Satisfy Gate 1 (unblock)

**Owner:** Anyone with a Rust toolchain (rust 1.93.0 per CI)

**Commands:**
```bash
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
cargo test --locked --workspace --all-features
cargo build --locked              # default features unchanged
cargo build --locked --features nuvio  # nuvio feature compiles
```

**Expected:** Exit code 0 for all. 8 nuvio tests pass. No clippy warnings. No formatting diffs.

**If blocked:** Record the exact error, exit code, and command. Do not proceed to Phase 2 until Gate 1 passes.

## Step 2: Phase 2 scoping (BLOCKED until Gate 1 + Nuvio producer contract)

**Do not implement** a Nuvio service, Continue Watching feed, or stack row yet. The repository has no Nuvio producer API.

**When a Nuvio owner authorizes a publish contract, the bounded work is:**

1. Add `"nuvio"` to `stacks.rs::SOURCES`
2. `has_library("nuvio")` → true
3. `collection_choices("nuvio")` returns `["continue-watching", "watchlist", "library"]`
4. Create `src/nuvio.rs` (planned) consumer service (read-only, profile-scoped, cancellation tokens, bounded item counts)
5. Wire `stacks_refresh()` in `main.rs` to send `Nuvio::Command::Fetch`
6. Consumer-side tests with synthetic fixtures
7. Producer-side implementation proposal for the Nuvio repository (separate repo)

**Constraints:**
- No unauthenticated LAN endpoint
- No Nuvio account/profile storage in Luma
- No Nuvio playback engine in Luma
- Luma only launches `contentTarget` via `Request::NuvioLaunch` (already implemented in Phase 1)

## Step 3: Phase 3 (BLOCKED until Phase 2)

Evaluate rendering Nuvio Continue Watching as a Home row. Reuses `stacks_view.rs` — no new rendering system.

## What NOT to do next

- Do not create an independent Nuvio UI framework
- Do not create a new general-purpose API server
- Do not fabricate Continue Watching feeds or duplicate Nuvio state
- Do not run physical TV operations or device installation
- Do not proceed to Phase 2 until Gate 1 passes
