# Nivío Phase 2 — Continue Watching Stack Row

**Architectural principle:** Reuse before adapting. Adapt before creating. Only CREATE when no existing owner can satisfy the requirement.

**Status:** BLOCKED — No Nuvio producer API exists in this repository. Consumer-side interface can be designed and tested with synthetic fixtures, but no producer integration can be implemented without authorization.

**Working branch:** `arena/5fe14abb-luma-webos-launcher` (PR #2, open draft)

## 1. Existing Components That Phase 2 Reuses

| Component | Owner File | Phase 2 Role | Change Needed |
|---|---|---|---|
| Stacks source registry | `src/stacks.rs` | `SOURCES`, `has_library()`, `collection_choices()`, `source_name()` | ADAPT — add `"nuvio"` entry |
| Stack item model | `src/stacks.rs::StackItem` | Poster + title + id per card | REUSE — no change |
| Stack card rendering | `src/stacks_view.rs` | `home_stacks()` renders any source generically | REUSE — no change |
| Source label | `src/stacks_view.rs::source_label()` | Display "Nuvio" beside row title | ADAPT — add `"nuvio" => "Nuvio"` |
| Platform worker pattern | `src/platform.rs::Service` | Worker thread, Command/Response channels | REUSE pattern — new `src/nuvio.rs` |
| StackItems state | `src/state.rs::stack_items` | `Vec<Vec<StackItem>>` per stack row | REUSE — no change |
| Stacks refresh | `src/main.rs::stacks_refresh()` | Triggers `Command::Fetch` per linked source | ADAPT — add nuvio branch |
| Response handler | `src/main.rs::jellyfin_tick()` / `plex_tick()` | `Response::Items(index, items)` → `state.stack_items[index]` | ADAPT — add nuvio tick arm |
| Duplicate launch block | `src/state.rs::state.launching` | `!self.launching` guard on `Target::NuvioLaunch` | REUSE — Phase 1 already covers |
| Focus preservation | `src/state.rs::activate()` | Focus unchanged on launch | REUSE — Phase 1 already covers |
| Back restoration | `src/state.rs::back()` | Existing Back chain, no Nuvio insertion | REUSE — no change |
| Poster caching | `src/media.rs::download_as()`, `src/app_artwork.rs` | Bounded download + cache | REUSE — no change |
| Empty row skipping | `src/stacks.rs::visible_rows()` | Empty rows not rendered | REUSE — no change |
| Translations | `assets/messages.json` | `nuvioContinueWatching`, `nuvioWatchlist`, `nuvioLibrary` | ADAPT — add 5 locales |

## 2. Components That Phase 2 Creates

| Component | Owner File | Why CREATE | Feature-gated? |
|---|---|---|---|
| Nivío consumer service | `src/nuvio.rs` (new) | No existing component fetches Nivío Continue Watching | Yes (`#[cfg(feature = "nuvio")]`) |
| Nivío `Command::Fetch` | `src/nuvio.rs` | No existing command fetches Nivío stack items | Yes |
| Nivío `Response::Items(index, items)` | `src/nuvio.rs` | No existing response carries Nivío stack items | Yes |
| Nivío service accessor | `src/main.rs::nuvio_service()` | No existing `OnceLock` service for Nivío | Yes |
| Nivío tick handler | `src/main.rs::nuvio_tick()` | No existing tick drains Nivío responses | Yes |
| Consumer tests | `src/tests.rs::mod nuvio` (Phase 2) | No existing test covers Nivío stack fetch | Yes |

## 3. Detailed Design

### 3.1 `src/stacks.rs` changes

Add `"nuvio"` to `SOURCES`:

```rust
pub const SOURCES: [(&str, &str, bool); 4] = [
    ("moonlight", "Moonlight", true),
    ("jellyfin", "Jellyfin", true),
    ("plex", "Plex", true),
    ("nuvio", "Nuvio", true),
];
```

Update `has_library()`:

```rust
pub fn has_library(source: &str) -> bool {
    matches!(source, "moonlight" | "jellyfin" | "plex" | "nuvio")
}
```

Update `collection_choices()` — add nuvio arm returning future collections:

```rust
if state
    .preferences
    .stacks
    .get(stack)
    .is_some_and(|s| s.source == "nuvio")
{
    return vec![
        ("continue-watching".to_owned(), "Continue Watching".to_owned()),
        ("watchlist".to_owned(), "Watchlist".to_owned()),
        ("library".to_owned(), "Library".to_owned()),
    ];
}
```

Update `row_title()` — nuvio uses `collection_label()`:

```rust
if stack.source == "nuvio" {
    return collection_label(stack);
}
```

Update `collection_label()` — nuvio collections:

```rust
if stack.source == "nuvio" {
    return match stack.collection.as_str() {
        "continue-watching" => "Continue Watching",
        "watchlist" => "Watchlist",
        "library" => "Library",
        _ => stack.list_title.clone(),
    }
    .to_owned();
}
```

### 3.2 `src/stacks_view.rs` changes

Add to `source_label()`:

```rust
fn source_label(source: &str) -> &'static str {
    match source {
        "media" => "Media",
        "moonlight" => "Moonlight",
        "jellyfin" => "Jellyfin",
        "plex" => "Plex",
        "nuvio" => "Nuvio",
        _ => "",
    }
}
```

### 3.3 `src/nuvio.rs` (new file)

Follow the Jellyfin/Plex `Service` pattern exactly:

```rust
//! Nivío Continue Watching consumer service. Luma never constructs playback
//! targets; Nuvío's deep-link receiver owns detail pages. Luma only fetches
//! stack items (title, poster, contentTarget) and renders them as cards.
use crate::stacks::StackItem;
use serde_json::Value;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Mutex, mpsc};
use std::thread;

pub enum Command {
    /// Cards for (stack index, collection id).
    Fetch(Vec<(usize, String)>),
}

pub enum Response {
    Items(usize, Vec<StackItem>),
}

pub struct Service {
    sender: Mutex<mpsc::Sender<Command>>,
    pub receiver: Mutex<mpsc::Receiver<Response>>,
}

static FETCH_ATTEMPT: AtomicU64 = AtomicU64::new(0);

impl Service {
    pub fn new(_cache: PathBuf) -> Self {
        let (sender, commands) = mpsc::channel::<Command>();
        let (reply, receiver) = mpsc::channel();
        thread::spawn(move || {
            for command in commands {
                match command {
                    Command::Fetch(stacks) => fetch(&reply, stacks),
                }
            }
        });
        Self {
            sender: Mutex::new(sender),
            receiver: Mutex::new(receiver),
        }
    }

    pub fn send(&self, command: Command) {
        let _ = self.sender.lock().unwrap().send(command);
    }
}

/// Bounded fetch: at most one collection per stack, at most 20 items per
/// collection. Synthetic fixtures used until a Nivío producer contract exists.
fn fetch(reply: &mpsc::Sender<Response>, stacks: Vec<(usize, String)>) {
    for (index, collection) in stacks {
        let items = match collection.as_str() {
            "continue-watching" => continue_watching_items(),
            "watchlist" => watchlist_items(),
            "library" => library_items(),
            _ => vec![],
        };
        let _ = reply.send(Response::Items(index, items));
    }
}

/// Synthetic Continue Watching items — replaced by real Nivío producer API.
fn continue_watching_items() -> Vec<StackItem> {
    vec![
        StackItem {
            title: "Example Movie".into(),
            poster: None,
            id: 1,
        },
    ]
}

/// Synthetic Watchlist items — replaced by real Nivío producer API.
fn watchlist_items() -> Vec<StackItem> {
    vec![]
}

/// Synthetic Library items — replaced by real Nivío producer API.
fn library_items() -> Vec<StackItem> {
    vec![]
}
```

### 3.4 `src/main.rs` changes

Add `nuvio_service()` accessor (after `jellyfin_service()` / `plex_service()`):

```rust
fn nuvio_service() -> &'static nuvio::Service {
    static SERVICE: std::sync::OnceLock<nuvio::Service> = std::sync::OnceLock::new();
    SERVICE.get_or_init(|| {
        let cache = if std::path::Path::new("/media/developer/com.denisefremov.luma").exists() {
            std::path::PathBuf::from("/media/developer/com.denisefremov.luma/posters")
        } else {
            std::env::temp_dir().join("luma-posters")
        };
        nuvio::Service::new(cache)
    })
}
```

Add nuvio branch to `stacks_refresh()`:

```rust
if state.preferences.stacks.iter().any(|s| s.source == "nuvio") {
    let wanted = state
        .preferences
        .stacks
        .iter()
        .enumerate()
        .filter(|(_, s)| s.source == "nuvio")
        .map(|(i, s)| (i, s.collection.clone()))
        .collect::<Vec<_>>();
    if !wanted.is_empty() {
        nuvio_service().send(nuvio::Command::Fetch(wanted));
    }
}
```

Add nuvio tick handler (after `jellyfin_tick()` / `plex_tick()` pattern):

```rust
fn nuvio_tick(state: &mut State) {
    while let Ok(response) = nuvio_service().receiver.lock().unwrap().try_recv() {
        state.dirty = true;
        match response {
            nuvio::Response::Items(index, items) => {
                if state.stack_items.len() <= index {
                    state.stack_items.resize(index + 1, vec![]);
                }
                state.stack_items[index] = items;
            }
        }
    }
}
```

Call `nuvio_tick(state)` in the main run loop alongside `jellyfin_tick()` and `plex_tick()`.

### 3.5 `src/main.rs` Effect handler (optional)

If Nivío stack cards should launch via `Effect::NuvioLaunch` (Phase 1 path), the card's `contentTarget` must be carried in `StackItem`. Currently `StackItem` has `id: i64` and `title: String` and `poster: Option<String>`. Two options:

**Option A (minimal):** StackItem.id maps to TMDB id; `Target::StackCard(row, index)` → `Effect::NuvioLaunch { content_target: format!("nuvio://tmdb/movie/{}", id) }`. Requires `StackItem` to carry source hint or a new `Target::NuvioStackCard` variant.

**Option B (full):** Add `content_target: String` to `StackItem`. Card activation reads it directly.

**Recommendation:** Option B — add `content_target: String` to `StackItem` (default empty). Existing sources leave it empty; Nivío sets it. `state.activate()` handles `Target::StackCard` with non-empty `content_target` → `Effect::NuvioLaunch`.

### 3.6 Translations (`assets/messages.json`)

Add keys in all 5 locales (en, de, es, zh, pt):

- `nuvioContinueWatching` — "Continue Watching"
- `nuvioWatchlist` — "Watchlist"  
- `nuvioLibrary` — "Library"

Follow the existing `appOpenError` / `nuvioNotInstalled` pattern.

## 4. Consumer-Side Tests (Phase 2)

Following the Phase 1 test module pattern, add to `src/tests.rs`:

```rust
#[cfg(feature = "nuvio")]
mod nuvio {
    use super::*;

    #[test]
    fn nuvio_fetch_returns_items_for_collections() {
        // Synthetic: continue-watching returns 1 item, watchlist/library empty
    }

    #[test]
    fn nuvio_fetch_bounded_to_20_items() {
        // Verify fetch never exceeds HOME_ROW_MAX per collection
    }

    #[test]
    fn nuvio_response_items_maps_to_stack_index() {
        // Verify Response::Items(index, items) → state.stack_items[index]
    }
}
```

## 5. Dependencies (No New Crates)

Phase 2 uses only existing dependencies: `serde_json`, `std::sync::mpsc`, `std::thread`. No new Cargo.toml entries.

## 6. Rollback (Non-Destructive)

Per established rollback guidance: `git revert` only. The Nivío feature is `#[cfg(feature = "nuvio")]` gated and off by default, so removal is a feature-flag toggle plus source reversion. Destructive history-rewriting operations are prohibited on shared branches.

## 7. Measurement & QA

| Check | Method | Pass Criterion |
|---|---|---|
| `cargo fmt --all -- --check` | CI | Zero diff |
| `cargo clippy --locked --workspace --all-features -- -D warnings` | CI | Zero warnings |
| `cargo test --locked --workspace --all-features` | CI | All tests pass |
| `cargo build --no-default-features` | CI | Builds without nuvio feature |
| `cargo build --features nuvio` | CI | Builds with nuvio feature |

---

# Multi-Agent Memory & Task Coordination System

**Goal:** Enable cloud (Arena) and local agents (Claude, Codex, Kimi, etc.) to share memories, lessons, tasks, and workspace state efficiently across multiple agents and workspaces.

**Design constraints:**
- No Rust toolchain in sandbox → Python/JSONL/SQLite (stdlib only)
- No network dependency for local operation
- Append-only, crash-safe, concurrent-read safe
- Human-readable and machine-parseable
- Cross-agent attribution (who wrote what, when, from where)

## 1. Architecture Overview

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Cloud Agent   │      │  Local Agent A  │      │  Local Agent B  │
│   (Arena/You)   │      │   (Claude)      │      │   (Codex)       │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   Shared Coordination Layer│
                    │  (repo/.agent-memory/)     │
                    │  ├── tasks.jsonl            │
                    │  ├── memories.db (SQLite)   │
                    │  ├── lessons.jsonl          │
                    │  └── workspace-state.json   │
                    └─────────────────────────────┘
```

## 2. Data Formats

### 2.1 Tasks (`tasks.jsonl`) — append-only task log

One JSON object per line. Fields:
- `id` — ULID or UUID
- `type` — `feature` | `bug` | `refactor` | `docs` | `test` | `infra`
- `title` — human-readable
- `description` — full details
- `status` — `open` | `in_progress` | `review` | `done` | `blocked`
- `assignee` — agent name (e.g., `arena`, `claude`, `codex`, `kimi`)
- `workspace` — branch or worktree path
- `created_at` — ISO-8601
- `updated_at` — ISO-8601
- `depends_on` — list of task IDs
- `hash` — SHA-256 of content for integrity
- `parent_task` — optional parent task ID for decomposition

### 2.2 Memories (`memories.db` — SQLite)

Structured, queryable memory store. Tables:

```sql
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,          -- pattern | decision | lesson | anti-pattern | hidden-gem
    domain TEXT NOT NULL,        -- rust | ui | webos | ci | agent-coord
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    evidence TEXT,               -- file:line references, commit SHAs
    confidence REAL NOT NULL,    -- 0.0-1.0
    source_agent TEXT NOT NULL,
    source_workspace TEXT,
    created_at TEXT NOT NULL,
    last_accessed TEXT,
    access_count INTEGER DEFAULT 0,
    tags TEXT                    -- JSON array
);

CREATE TABLE IF NOT EXISTS lessons_learned (
    id TEXT PRIMARY KEY,
    situation TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    outcome TEXT NOT NULL,
    what_we_would_do_differently TEXT,
    source_agent TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_dependencies (
    task_id TEXT NOT NULL,
    depends_on TEXT NOT NULL,
    PRIMARY KEY (task_id, depends_on)
);
```

### 2.3 Lessons (`lessons.jsonl`) — append-only lesson log

One JSON object per line. Fields:
- `id`, `situation`, `action_taken`, `outcome`, `what_we_would_do_differently`, `source_agent`, `created_at`

### 2.4 Workspace State (`workspace-state.json`)

Snapshot of current workspace:
```json
{
  "branch": "arena/5fe14abb-luma-webos-launcher",
  "head_sha": "2280046",
  "active_prs": [1, 2],
  "blocked_on": ["nuvio-producer-api"],
  "ci_status": {"docs": "passing", "rust": "failing"},
  "last_sync": "2026-11-05T..."
}
```

## 3. Coordination Protocol

### 3.1 Agent Registration

On startup, each agent writes its presence:
```json
{"type": "agent_register", "agent": "claude", "workspace": "/home/user/luma-webos-launcher", "capabilities": ["rust", "docs", "qa"], "at": "2026-11-05T..."}
```

### 3.2 Task Claiming

1. Agent scans `tasks.jsonl` for `status == "open"` tasks not assigned
2. Atomically claims by appending an update: `{"id": "...", "status": "in_progress", "assignee": "claude", ...}`
3. Other agents see the claim and skip

### 3.3 Memory Sharing

1. Agent writes lessons/patterns to `lessons.jsonl` and `memories.db`
2. Other agents query `memories.db` before starting work
3. Confidence scores weight memory relevance

### 3.4 Conflict Resolution

- JSONL is append-only: last write wins for same key, but history preserved
- SQLite uses WAL mode for concurrent reads
- Agent attribution prevents orphaned changes

## 4. Implementation Plan

### Phase A: Core Coordination Layer (stdlib Python)

Create `.agent-memory/` directory with:

1. `agent_memory.py` — Python module with:
   - `TaskLog` — append/read/query tasks.jsonl
   - `MemoryStore` — SQLite memories.db wrapper
   - `LessonLog` — append/read lessons.jsonl
   - `WorkspaceState` — read/write workspace-state.json
   - `AgentRegistry` — agent presence tracking

2. CLI interface: `python3 .agent-memory/agent_memory.py <command> [args]`

### Phase B: Task Decomposition for Nivío Phase 2

Break down Continue Watching into atomic tasks:

| Task ID | Type | Title | Depends On | Est. |
|---|---|---|---|---|
| T-001 | feature | Add "nuvio" to stacks.rs SOURCES | — | 0.5h |
| T-002 | feature | Add has_library("nuvio") → true | T-001 | 0.25h |
| T-003 | feature | Add collection_choices("nuvio") | T-001 | 0.5h |
| T-004 | feature | Add source_label("nuvio") | — | 0.25h |
| T-005 | feature | Create src/nuvio.rs Service | — | 2h |
| T-006 | feature | Wire stacks_refresh() nuvio branch | T-005 | 0.5h |
| T-007 | feature | Add nuvio_tick() in main.rs | T-005 | 0.5h |
| T-008 | feature | Add content_target to StackItem | — | 0.5h |
| T-009 | feature | Handle StackCard → NuvioLaunch | T-008, T-005 | 1h |
| T-010 | test | Consumer-side synthetic tests | T-005 | 1h |
| T-011 | docs | Update REUSE-MATRIX.md Phase 2 | T-001..T-010 | 0.5h |
| T-012 | qa | cargo fmt + clippy + test (CI) | T-001..T-010 | 1h |

### Phase C: Agent Integration Hooks

1. Pre-work hook: agent reads `tasks.jsonl` + `memories.db` before starting
2. Post-work hook: agent writes lessons/memory + updates task status
3. CI hook: validation runs on task completion

## 5. Research: How Others Solved This

| System | Approach | Relevant Pattern for Luma |
|---|---|---|
| Claude Code / Claude Flow | JSONL memory + task queue | Append-only logs, agent attribution |
| GitHub Copilot Workspace | Task decomposition + dependency graph | Task IDs, depends_on, status tracking |
| Linear.app | Task states + assignees + priorities | Open/in_progress/review/done/blocked |
| SQLite WAL mode | Concurrent read, single write | WAL for crash-safe concurrent access |
| ULID | Sortable unique IDs | Time-ordered, URL-safe, no coordination needed |

## 6. Hidden Gems & Patterns to Revise

### Hidden Gems in Existing Luma Code:
1. **`state.launching` flag** — already provides duplicate-launch protection; reusable for any async fetch
2. **`#[cfg(feature = "nuvio")]`** — feature gating means Nivío code compiles out when disabled; zero cost for default builds
3. **`Response::Items(index, items)`** — Jellyfin/Plex already prove the stack-item fetch pattern works
4. **`stacks::visible_rows()`** — already skips empty rows; Nivío empty collections render nothing
5. **`StackItem` struct** — already has `id`, `title`, `poster`; only needs `content_target` for Nivío cards

### Patterns to Revise:
1. **Hardcoded `/home/user/` paths** in `tools/validate_docs.py` — already fixed in P0
2. **`shutil.rmtree()` in tests** — already fixed in P0 with `TemporaryDirectory()`
3. **No cross-agent memory** — this proposal addresses that gap
4. **Nivío docs scattered** — consolidated in REUSE-MATRIX.md, USER-FLOWS.md, COMPONENTS.md

## 7. Measurement & QA

| Metric | Target | Measurement |
|---|---|---|
| Task claim latency | < 30s | Time from task open to claim |
| Memory query latency | < 100ms | SQLite query time |
| CI rustfmt pass | 100% | `cargo fmt --check` |
| CI clippy pass | 0 warnings | `cargo clippy -D warnings` |
| CI test pass | 100% | `cargo test --all-features` |
| Doc validation pass | 0 errors | `tools/validate_docs.py` |
| Negative test pass | 15/15 | `tools/test_validate_docs.py` |

## 8. Responsibilities

| Role | Responsibility |
|---|---|
| **PM** | Task prioritization, dependency tracking, blocker escalation |
| **QA** | Rustfmt/clippy/test validation, negative test suite, CI monitoring |
| **Dev** | Feature implementation, code reviews, rollback execution |
| **Forensics** | SHA tracking, commit attribution, diff analysis, root cause |
| **Agent Coord** | Memory store maintenance, task log hygiene, cross-agent sync |

## 9. Safety Constraints (Do Not)

- ❌ Do not merge to main without CI green
- ❌ Do not access physical TV
- ❌ Do not enable root hooks
- ❌ Do not begin live Continue Watching integration (blocked on producer contract)
- ❌ Do not use destructive history-rewriting operations on shared branches
- ❌ Do not claim unexecuted tests as PASS
- ❌ Do not fake hardware measurements

---
