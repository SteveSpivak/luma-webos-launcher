# L0 System Atlas — Luma WebOS Launcher

**Purpose**: Macro-level topology of the entire repository. Every agent starts
here. Under 2,000 tokens total. Contains C4 context, container boundaries, and
core invariants.

---

## C4 Context Diagram (Text)

```
┌─────────────────┐      deep-link       ┌──────────────────┐
│  Luma Launcher  │─────────────────────▶│  Nuvio Lab App   │
│  (this repo)    │   nuvio://tmdb/…     │  space.nuvio.lab │
└─────────────────┘   (feature-gated)    └──────────────────┘
         │
         │ deep-link (production, never touched by Luma)
         ▼
┌──────────────────┐
│ Nuvio WebOS App  │
│ space.nuvio.webos│
└──────────────────┘

         │ read-only LCKV bridge
         ▼
┌──────────────────┐
│  /tmp/nuvio_     │
│  _stacks.lckv    │ 32B header + 396B/card + 8B trailer
│  (produced by    │ max 40 cards, 16,384B budget
│   NuvioTV)       │
└──────────────────┘
```

---

## Container Boundaries

| Container | Responsibility | Key Files | Feature Gate |
|-----------|---------------|-----------|--------------|
| **Luma Launcher (bin)** | Home screen, app tiles, media stacks, rendering | `src/main.rs`, `src/state.rs`, `src/renderer.rs`, `src/view.rs` | None (default build) |
| **Platform (Luna IPC)** | TV service calls, app launch, Nuvio deep-link | `src/platform.rs` | `webos` for native Luna, `nuvio` for NuvioLaunch |
| **Nuvio Consumer** | LCKV bridge reading, Continue Watching cards | `src/nuvio.rs`, `src/fast_kv.rs` | `nuvio` |
| **Nuvio Lab** | Isolated test target `space.nuvio.lab` | `src/main.rs` `lab_command()`, `src/platform.rs` `nuvio_app_id()` | `nuvio_lab` |

---

## Core Invariants (Never Violate)

1. **Production isolation**: `space.nuvio.webos` is never modified, launched, or replaced by Luma code.
2. **Lab opt-in**: `space.nuvio.lab` is only used when `nuvio_lab` feature is compiled AND `lab=true` is passed at runtime.
3. **No silent override**: `nuvio_app_id(true)` falls back to `NUVIO_APP_ID` if `nuvio_lab` feature is not compiled.
4. **Read-only consumer**: `read_bridge_cards()` takes `&path`; no write path in consumer code.
5. **Seqlock integrity**: Reader accepts file only when `head == tail && even`.
6. **Focus preservation**: `Target::NuvioLaunch` does not modify focus; Back returns to same focus.
7. **No duplicate routing**: Single `Platform::send()` path for all launches.
8. **Fail closed**: `validate_nuvio_target()` rejects anything not matching `nuvio://tmdb/{movie|tv}/<digits>`.
9. **No VRAM clearing**: `self.textures.clear()` is forbidden.
10. **No freeze on FocusLost**: When window still visible, renderer continues.

---

## Data Flow: Nuvio Lab Deep-Link

```
User clicks Lab card
    │
    ▼
state.activate() → Effect::NuvioLaunch { content_target }
    │
    ▼
main.rs: Effect handler → platform.send(Request::NuvioLaunch { content_target })
    │
    ▼
platform.rs: Platform::send() → worker thread → Request::NuvioLaunch match arm
    │
    ▼
validate_nuvio_target(content_target) → Ok(target) or Err("Invalid Nuvio content target")
    │
    ▼
nuvio_app_id(lab=true) → "space.nuvio.lab" (if feature compiled) or "space.nuvio.webos" (fallback)
    │
    ▼
nuvio_launch_params_lab(target) → {"id": "space.nuvio.lab", "params": {"contentTarget": target}}
    │
    ▼
call("luna://com.webos.applicationManager/launch", payload) → TV launches Lab app
    │
    ▼
Focus untouched → Back out of Lab returns to Luma with same focus
```

---

## Data Flow: LCKV Continue Watching Consumer

```
NuvioTV producer writes /tmp/nuvio_stacks.lckv
    │
    ▼
nuvio::Service::fetch() → bridge_items(&bridge_path, "continue-watching")
    │
    ▼
fast_kv::read_bridge_cards(path, "continue-watching")
    │
    ├─ File missing → None → synthetic fallback
    ├─ File present, empty → Some(vec![]) → valid empty (show nothing)
    ├─ File present, cards → Some(vec![StackItem...])
    │
    ▼
bridge_items() converts cards to StackItem with:
  - id: unique_card_id(card_id, content_target) [FNV-1a-64, position-independent]
  - content_target: from card
  - progress_permille: from card
  - poster_url / still_url: Metahub CDN from "tt" id
    │
    ▼
nuvio_tick() → state.stack_items[index] = items
    │
    ▼
Renderer displays Continue Watching cards
    │
    ▼
User clicks card → Effect::NuvioLaunch → deep-link to Nuvio
```

---

## Branch Topology

| Branch | Base | Status | Notes |
|--------|------|--------|-------|
| `main` | — | Production | `origin/main` at `40994fc`; compiles on stable Rust 0 errors |
| `arena/5fe14abb-luma-webos-launcher` | `main` | PR #2 open | Nuvio Lab integration; fixes in progress |
| `arena/luma-phase1-tv` | — | TV build | Known-good TV build branch; Option A target |

---

## Navigation

- `.agent-kb/architecture/L2_MODULES/` — Per-module detailed capsules
- `.agent-kb/flows/` — E2E sequence and state diagrams
- `.agent-kb/dependencies/` — Coupling and SBOM
- `.agent-kb/memories_and_lessons/` — Laws and failure lessons
- `.agent-kb/labs/` — Executable verification sandboxes
- `.agent-kb/views/` — Role-specific projections
