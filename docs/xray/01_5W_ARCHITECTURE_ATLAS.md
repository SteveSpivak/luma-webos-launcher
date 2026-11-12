# 5-W Architecture Atlas

> ⚡ **BLUF**: Single-source architectural map of the Luma webOS launcher. Every
> module, boundary, and invariant is cited to real `file:line` coordinates so no
> agent ever guesses where logic lives. Companion to `docs/xray/README.md` (L0
> summary) and `docs/xray/MERMAID_DIAGRAMS.md` (rich web UI).

+-----------------------------------------------------------------------------+
| 5-W + H ARCHITECTURE MAP                                                    |
+-----------------------------------------------------------------------------+
|                                                                             |
|  WHAT   WebOS native launcher with Phase 1 Nuvio deep-link + LCKV consumer  |
|  WHY    Let users launch Nuvio titles from cards on opt-in; isolated lab    |
|         target `space.nuvio.lab` never touches production `space.nuvio.webos`|
|  WHERE  `src/main.rs` entry  `src/platform.rs` Luna IPC  `src/state.rs` FSM |
|         `src/fast_kv.rs` LCKV bridge  `src/nuvio.rs` consumer  `src/renderer.rs` UI |
|  WHEN   On card click → Effect::NuvioLaunch → Platform::send() → Luna launch|
|  WHO    Upstream: UI card click  Downstream: Nuvio TV app  Owner: Luma team |
|  HOW    validate_nuvio_target() → nuvio_app_id(lab) → nuvio_launch_params() |
|         → call("luna://com.palmdtv.applauncher/launch")                     |
+-----------------------------------------------------------------------------+

## Module Directory (L1 → L2 → L3)

| Domain | Module (L2) | Key Symbols (L3) | File | Risk |
|--------|------------|------------------|------|------|
| App launch to TV | `platform` | `Platform`, `Request`, `Response`, `NUVIO_APP_ID`, `NUVIO_LAB_APP_ID`, `validate_nuvio_target()` | [`src/platform.rs`](src/platform.rs#L20-L60) | 🟡 [COUPLED] |
| UI state & navigation | `state` | `State`, `Effect`, `Target`, `Preferences` | [`src/state.rs`](src/state.rs#L30-L50) | 🟡 [COUPLED] |
| Rendering scene | `renderer` | `Renderer`, `draw_mesh()`, `flush_quad_batcher()` | [`src/renderer.rs`](src/renderer.rs#L2320-L2360) | 🔴 [RADIOACTIVE] |
| Stack rows | `stacks` | `StackItem`, `StackConfig`, `row_stack()` | [`src/stacks.rs`](src/stacks.rs#L8-L25) | 🟡 [COUPLED] |
| Nuvio consumer | `nuvio` | `Service`, `Command`, `Response`, `bridge_items()` | [`src/nuvio.rs`](src/nuvio.rs#L50-L70) | 🟢 [STABLE] |
| LCKV binary bridge | `fast_kv` | `read_bridge_cards()`, `write_bridge_cards()`, `fnv1a_64()` | [`src/fast_kv.rs`](src/fast_kv.rs#L120-L140) | 🟢 [STABLE] |
| Main entry / lab | `main` | `main()`, `lab_command()`, `nuvio_service()`, `nuvio_tick()` | [`src/main.rs`](src/main.rs#L2085-L2100) | 🟡 [COUPLED] |

## Core Invariants (Never Violate)

| # | Invariant | Evidence |
|---|-----------|----------|
| 1 | `space.nuvio.webos` never modified/launched/replaced by Luma | [`src/platform.rs#L25`](src/platform.rs#L25) |
| 2 | `space.nuvio.lab` only used when `nuvio_lab` feature + `lab=true` | [`src/platform.rs`](src/platform.rs) `nuvio_app_id()` |
| 3 | No silent runtime override of production app ID | [`src/platform.rs`](src/platform.rs) falls back to production if feature missing |
| 4 | LCKV consumer is read-only | [`src/fast_kv.rs`](src/fast_kv.rs) `read_bridge_cards(path, collection)` takes `&path` |
| 5 | Seqlock: `head == tail && even` required | [`src/fast_kv.rs#L124-L130`](src/fast_kv.rs#L124-L130) |
| 6 | Empty bridge = `Some(vec![])`, not synthetic fallback | [`src/nuvio.rs`](src/nuvio.rs) `bridge_items()` |
| 7 | Focus untouched during Nuvio launch | [`src/state.rs`](src/state.rs) `Target::NuvioLaunch` doesn't modify `state.focus` |
| 8 | `!self.launching` guard prevents duplicate launches | [`src/state.rs`](src/state.rs), [`src/main.rs`](src/main.rs) |
| 9 | No `self.textures.clear()` or VRAM clearing | Council verdict — absent from codebase |
| 10 | No `if let` guards on Rust 1.93 CI pin | [`src/renderer.rs#L2030-L2040`](src/renderer.rs#L2030-L2040) fails on 1.93 |

## Mermaid: Module Dependency Graph

```mermaid
graph TD
    main[src/main.rs: main() entry] --> platform[src/platform.rs: Luna IPC]
    main --> state[src/state.rs: FSM + launch guard]
    main --> renderer[src/renderer.rs: draw_mesh]
    platform --> nuvio[src/nuvio.rs: Nuvio consumer]
    platform --> luna["luna://com.palmdtv.applauncher/launch"]
    nuvio --> fastkv[src/fast_kv.rs: LCKV bridge read-only]
    state --> stacks[src/stacks.rs: StackItem rows]
    renderer --> stacks
```
