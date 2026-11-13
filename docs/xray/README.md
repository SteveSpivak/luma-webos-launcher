> ⚡ **BLUF (30-Second Executive Summary)**
> - **What**: Luma is a remote-first native launcher for rooted LG webOS TVs, with Phase 1 Nuvio deep-link integration and a read-only LCKV binary bridge consumer for Continue Watching cards.
> - **Why**: Luma asks Nuvio to open titles on user opt-in; production `space.nuvio.webos` is never modified by Luma. Lab target `space.nuvio.lab` is feature-gated for isolated testing.
> - **Where**: Entry point `src/main.rs`; platform layer `src/platform.rs`; LCKV consumer `src/nuvio.rs` + `src/fast_kv.rs`; UI state `src/state.rs`; renderer `src/renderer.rs`.
> - **When**: Builds on stable Rust 1.96.0 (CI pin 1.93.0 — too old for `if let` guards). CI runs on `ubuntu-24.04` via GitHub Actions.
> - **Who**: Cloud agent writes code; local macOS agent runs `cargo` gates; GitHub Actions CI validates before PR #2 merge.
> - **How**: `cargo fmt --all --check`, `cargo check --features nuvio,nuvio_lab`, `cargo test --all-features`, `cargo clippy --all-targets --all-features -- -D warnings`. No local Rust toolchain — cloud sandbox is python3/bash only.

+-----------------------------------------------------------------------------+
| ASCII MODULE OVERVIEW: ENTRY → PLATFORM → LUNA IPC → NUVIO TV APP         |
+-----------------------------------------------------------------------------+
|                                                                             |
|  [src/main.rs]  lab=true + nuvio_lab feature                                |
|         |                                                                   |
|         v                                                                   |
|  [src/platform.rs]  nuvio_app_id(lab)                                       |
|         |  space.nuvio.lab  /  space.nuvio.webos                            |
|         v                                                                   |
|  call("luna://com.palmdtv.applauncher/launch")                              |
|         |                                                                   |
|         v                                                                   |
|  [Nuvio TV App]  opens title on user opt-in                                 |
|                                                                             |
+-----------------------------------------------------------------------------+
| RISK LEGEND:  🟢 STABLE  🟡 COUPLED  🔴 RADIOACTIVE                         |
+-----------------------------------------------------------------------------+

# Luma WebOS Launcher — Agent Knowledge Base (L0 System Atlas)

**Branch**: `arena/5fe14abb-luma-webos-launcher` | **Status**: `pr_open` (PR #2) | **Base**: `40994fc` (origin/main) | **Head**: `961d529`

---

## Domain → Module Lookup (L1 → L2 → L3)

| Domain | Module (L2) | Key Symbols (L3) | File | Risk Badge |
|--------|------------|------------------|------|------------|
| App launch to TV | `platform` | `Platform`, `Request`, `Response`, `NUVIO_APP_ID`, `NUVIO_LAB_APP_ID`, `validate_nuvio_target()` | `src/platform.rs` | 🟡 [COUPLED] |
| UI state & navigation | `state` | `State`, `Effect`, `Target`, `Preferences` | `src/state.rs` | 🟡 [COUPLED] |
| Rendering scene | `renderer` | `Renderer`, `draw_mesh()`, `flush_quad_batcher()` | `src/renderer.rs` | 🔴 [RADIOACTIVE] |
| Stack rows | `stacks` | `StackItem`, `StackConfig`, `row_stack()` | `src/stacks.rs` | 🟡 [COUPLED] |
| Nuvio consumer | `nuvio` | `Service`, `Command`, `Response`, `bridge_items()` | `src/nuvio.rs` | 🟢 [STABLE] |
| LCKV binary bridge | `fast_kv` | `read_bridge_cards()`, `write_bridge_cards()`, `fnv1a_64()` | `src/fast_kv.rs` | 🟢 [STABLE] |
| Main entry / lab | `main` | `main()`, `lab_command()`, `nuvio_service()`, `nuvio_tick()` | `src/main.rs` | 🟡 [COUPLED] |

---

## Core Invariants (Never Violate)

| # | Invariant | Evidence |
|---|-----------|----------|
| 1 | `space.nuvio.webos` never modified/launched/replaced by Luma | `src/platform.rs:25` |
| 2 | `space.nuvio.lab` only used when `nuvio_lab` feature + `lab=true` | `src/platform.rs` `nuvio_app_id()` |
| 3 | No silent runtime override of production app ID | `nuvio_app_id(true)` falls back to production if feature missing |
| 4 | LCKV consumer is read-only | `read_bridge_cards(path, collection)` takes `&path` |
| 5 | Seqlock: `head == tail && even` required | `src/fast_kv.rs:124-137` |
| 6 | Empty bridge = `Some(vec![])`, not synthetic fallback | `src/nuvio.rs` `bridge_items()` |
| 7 | Focus untouched during Nuvio launch | `Target::NuvioLaunch` doesn't modify `state.focus` |
| 8 | `!self.launching` guard prevents duplicate launches | `src/state.rs`, `src/main.rs` |
| 9 | No `self.textures.clear()` or VRAM clearing | Council verdict — absent from codebase |
| 10 | No `if let` guards on Rust 1.93 CI pin | `src/renderer.rs:2033` fails on 1.93 |

---

## 5 W's + H Matrix

| Dimension | Answer | Source |
|-----------|--------|--------|
| **WHAT** | WebOS TV launcher with Nuvio deep-link + LCKV Continue Watching consumer | `src/main.rs`, `src/platform.rs` |
| **WHY** | Phase 1: title-to-detail launch via Nuvio deep-link; isolated lab target for testing | `docs/CHARTER.md` |
| **WHERE** | `src/main.rs` entry, `src/platform.rs` Luna IPC, `src/fast_kv.rs` LCKV bridge | File paths above |
| **WHEN** | On user card click → `Effect::NuvioLaunch` → `Platform::send()` → Luna launch call | `src/state.rs`, `src/main.rs` |
| **WHO** | Upstream: UI card click; Downstream: Nuvio TV app; Owner: Luma team | `src/view.rs` → `src/platform.rs` |
| **HOW** | `validate_nuvio_target()` → `nuvio_app_id(lab)` → `nuvio_launch_params()` → `call("luna://...")` | `src/platform.rs` |

---

## Navigation

- `.agent-kb/architecture/L0_SYSTEM_ATLAS.md` — Detailed C4 architecture
- `.agent-kb/memories_and_lessons/SEMANTIC_MEMORY.md` — 20 architectural laws (SM-01 to SM-20)
- `.agent-kb/memories_and_lessons/EPISODIC_LESSONS.md` — 20 failure/fix episodes (EL-001 to EL-020)
- `.agent-kb/views/REVIEW_FAST_SCAN.md` — 5-phase PR review guide
- `scripts/fast-scan.sh` — Pre-CI fast scan (no Rust needed)
- `scripts/xray/scan_repo.py` — Deterministic forensic scanner
- `scripts/xray/xray_cli.py` — Fast query CLI (`impact`, `review`, `status`, `hotspots`, `branches`)
- `scripts/xray/verify_kb.py` — Automated quality gate (M1-M6)
