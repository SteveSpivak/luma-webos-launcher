# Luma WebOS Launcher — Agent Knowledge Base Index (L0 System Atlas)

**Purpose**: Single entry point for all agents (cloud, local macOS, CI) working on
this repository. Start here before reading any code. Contains the system map,
top 20 semantic memories / co-change traps, and a lookup table mapping domains
to module capsules.

**Branch**: `arena/5fe14abb-luma-webos-launcher` (status: `pr_open`, PR #2)
**Base commit**: `40994fc144b5af481056d14e2fb93304aa1e2c82` (origin/main)
**Current head**: See `git rev-parse HEAD`

---

## L0 System Map (One-Paragram Summary)

Luma is a remote-first native launcher for rooted LG webOS TVs. It runs as a
native application on the TV, manages a home screen with app tiles, media stacks
(Jellyfin, Plex, Moonlight games), smart home, widgets, and video wallpaper.
Phase 1 Nuvio integration adds deep-link launching of Nuvio titles via
`Effect::NuvioLaunch` and a read-only LCKV binary bridge consumer for Continue
Watching cards. The lab target (`space.nuvio.lab`) is feature-gated behind
`nuvio_lab` and never touches production `space.nuvio.webos`.

---

## Domain → Module Lookup (L1 → L2 → L3)

| Domain | Module (L2) | Key Symbols (L3) | File |
|--------|------------|------------------|------|
| App launch to TV | `platform` | `Platform`, `Request`, `Response`, `NUVIO_APP_ID`, `NUVIO_LAB_APP_ID`, `validate_nuvio_target()`, `nuvio_launch_params()` | `src/platform.rs` |
| UI state & navigation | `state` | `State`, `Effect`, `Target`, `Preferences` | `src/state.rs` |
| Rendering scene | `renderer` | `Renderer`, `draw_mesh()`, `flush_quad_batcher()`, `upload_stills()` | `src/renderer.rs` |
| Stack rows (home content) | `stacks` | `StackItem`, `StackConfig`, `row_stack()`, `row_shown()` | `src/stacks.rs` |
| App tiles / artwork | `app_artwork` | `Artwork`, `RawCachedTexture` | `src/app_artwork.rs` |
| Jellyfin media | `jellyfin` | `Service`, `Server` | `src/jellyfin.rs` |
| Plex media | `plex` | `Service` | `src/plex.rs` |
| Moonlight games | `moonlight` | `Host`, `Game` | `src/moonlight.rs` |
| Nuvio consumer service | `nuvio` | `Service`, `Command`, `Response`, `bridge_items()` | `src/nuvio.rs` |
| LCKV binary bridge | `fast_kv` | `read_bridge_cards()`, `write_bridge_cards()`, `FastBridgeCard`, `fnv1a_64()` | `src/fast_kv.rs` |
| Main entry / lab command | `main` | `main()`, `lab_command()`, `nuvio_service()`, `nuvio_tick()` | `src/main.rs` |
| Tests | `tests` | Unit tests for all modules | `src/tests.rs` |

---

## Top 20 Semantic Memories (Architectural Laws)

| # | Law | Source |
|---|-----|--------|
| 1 | Production `space.nuvio.webos` is never modified, launched, or replaced by Luma | CHARTER.md, user constraints |
| 2 | Lab target `space.nuvio.lab` is feature-gated behind `nuvio_lab`, off by default | Cargo.toml, platform.rs |
| 3 | No silent runtime override of production app ID | `nuvio_app_id(lab)` falls back to production |
| 4 | Invalid app IDs fail validation via `valid_app_id()` | `src/model.rs` |
| 5 | Test target visible in build metadata (`Cargo.toml` feature flag) | Cargo.toml |
| 6 | Test artifacts distinguishable from production (different app ID + PID-scoped temp fixture) | `src/main.rs` lab_command |
| 7 | No extra media launcher or duplicate routing layer | Single `Platform::send()` path |
| 8 | Rollback requires no production Nuvio application modification | Separate app ID, no production changes |
| 9 | LCKV consumer is read-only (`read_bridge_cards` takes `&path`) | `src/fast_kv.rs` |
| 10 | Seqlock: head == tail && even required; torn reads rejected | `src/fast_kv.rs` |
| 11 | Empty bridge returns `Some(vec![])`, not synthetic fallback | `src/nuvio.rs` `bridge_items()` |
| 12 | Focus untouched during Nuvio launch; Back returns to same focus | `src/state.rs` `Target::NuvioLaunch` |
| 13 | `!self.launching` guard prevents duplicate launches | `src/state.rs`, `src/main.rs` |
| 14 | No `self.textures.clear()`, no freeze on `FocusLost` when window visible | Council verdict |
| 15 | No experimental VRAM clearing, fixed decoder-drain delays, or new memory governor | Council verdict |
| 16 | `#[derive(Debug)]` on `Request` and `Response` enums for `payload_eq()` and test `panic!` | Round 1-2 fixes |
| 17 | `u8::is_ascii_digit` needs closure `|b: u8| b.is_ascii_digit()` on Rust 1.93 | Round 1-2 fixes |
| 18 | `mod nuvio` in tests shadows `crate::nuvio` — use explicit aliases | Round 2 fix |
| 19 | `rustfmt.toml` causes 141 fmt diffs — delete it, run `cargo fmt --all` | Round 1-2 fix |
| 20 | CI pin (Rust 1.93.0) is older than local stable (1.96.0) — `if let` guards fail | Round 2 finding |

---

## Top 10 Co-Change Traps (Files That Change Together)

| # | File A | File B | Jaccard | Trap |
|---|--------|--------|---------|------|
| 1 | `src/platform.rs` | `src/tests.rs` | High | Test references platform types that changed |
| 2 | `src/renderer.rs` | `src/state.rs` | High | Renderer borrows state immutably while mutating |
| 3 | `src/main.rs` | `src/stacks.rs` | High | `StackItem` fields changed, initializers not updated |
| 4 | `src/nuvio.rs` | `src/tests.rs` | High | Test module shadows crate module |
| 5 | `src/fast_kv.rs` | `src/nuvio.rs` | Medium | LCKV consumer depends on fast_kv types |
| 6 | `src/state.rs` | `src/platform.rs` | Medium | `Effect::NuvioLaunch` flows state → platform |
| 7 | `src/app_artwork.rs` | `src/renderer.rs` | Medium | Artwork textures fed to renderer |
| 8 | `Cargo.toml` | `src/tests.rs` | Medium | `tempfile` dev-dependency needed for tests |
| 9 | `src/main.rs` | `src/motion.rs` | Medium | Lab command calls motion test functions |
| 10 | `.github/workflows/ci.yml` | `Cargo.toml` | Medium | CI feature flags must match Cargo features |

---

## Quick Reference: 5 CI Gates

| Gate | Command | Local Cloud | Local macOS | GitHub Actions CI |
|------|---------|-------------|-------------|-------------------|
| Format | `cargo fmt --all --check` | ❌ No Rust | ✅ | ✅ Rust 1.93.0 |
| Check | `cargo check --features nuvio,nuvio_lab` | ❌ No Rust | ✅ | ✅ |
| Test | `cargo test --all-features` | ❌ No Rust | ✅ | ✅ |
| Clippy | `cargo clippy --all-targets --all-features -- -D warnings` | ❌ No Rust | ✅ | ✅ |
| Static verify | `python3 scripts/sandbox_verify.py` | ✅ | ✅ | N/A |

**Rule**: Cloud agent writes code and runs `scripts/fast-scan.sh` (python3 only).
Local macOS agent runs all 5 cargo gates. GitHub Actions CI runs final validation
before PR #2 can merge.

---

## Navigation

- `.agent-kb/architecture/L0_SYSTEM_ATLAS.md` — Detailed system architecture
- `.agent-kb/architecture/L2_MODULES/` — Per-module capsules
- `.agent-kb/flows/` — End-to-end data and control flows
- `.agent-kb/dependencies/` — Coupling, cycles, SBOM
- `.agent-kb/memories_and_lessons/SEMANTIC_MEMORY.md` — Architectural laws
- `.agent-kb/memories_and_lessons/EPISODIC_LESSONS.md` — Lessons from failures
- `.agent-kb/labs/` — Executable verification sandboxes
- `.agent-kb/views/REVIEW_FAST_SCAN.md` — PR fast-scan review guide
- `scripts/fast-scan.sh` — Pre-CI fast scan script
- `scripts/code-review-checklist.md` — Code review checklist
- `scripts/sandbox_verify.py` — Offline static analyzer (no Rust needed)
