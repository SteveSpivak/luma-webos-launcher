# Nuvio-to-Luma Reuse Matrix

Classification: REUSE / ADAPT / CREATE / REJECT. Existing components are prioritized. A component is only marked CREATE when no existing owner can satisfy the requirement.

## Phase 1 — Title-to-detail launch (committed, source-complete)

| Nuvio capability | Classification | Existing owner reused | Files changed | Rationale |
|---|---|---|---|---|
| App launch request | REUSE | Platform worker (`Request::Launch` pattern) | `src/platform.rs` | `Request::NuvioLaunch` follows the exact same worker pattern as `Request::Launch` / `Request::WebPlayer` / `Request::MoonlightLaunch`. |
| Fixed app ID | ADAPT | `valid_app_id()` validation | `src/platform.rs` | `NUVIO_APP_ID = "space.nuvio.webos"` is a new constant but uses the same validation contract as all other app IDs. |
| Content target validation | CREATE | None | `src/platform.rs` | `validate_nuvio_target()` is new — no existing function validates `nuvio://tmdb/` URLs. |
| Launch parameter construction | CREATE | `json!()` macro pattern | `src/platform.rs` | `nuvio_launch_params()` builds `{"id": NUVIO_APP_ID, "params": {"contentTarget": ...}}` — mirrors `Request::Launch` payload shape but is a new function. |
| Absent-app detection | ADAPT | `player_not_installed()` pattern | `src/platform.rs` | `app_not_installed()` is shared with WebPlayer; Nuvio adds `getAppInfo` preflight (same pattern as WebPlayer). |
| Launch response handling | REUSE | `Response::Launched` | `src/main.rs` | Same response variant used by Launch, WebPlayer, MoonlightLaunch, and now NuvioLaunch. |
| Duplicate launch blocking | REUSE | `state.launching` flag | `src/state.rs`, `src/main.rs` | The `!self.launching` guard already exists for all launch effects; NuvioLaunch is added to the same guard. |
| Focus preservation | REUSE | `state.activate()` focus model | `src/state.rs` | `Target::NuvioLaunch` does not move focus — same pattern as `Effect::Launch` which leaves focus for Back restoration. |
| Back restoration | REUSE | `state.back()` | None | Focus is untouched by Nuvio launch, so existing Back behavior returns to the same focus. No changes needed. |
| No autoplay | REUSE | Design decision | None | Luma only launches with `contentTarget`; Nuvio's deep-link receiver decides detail page vs. playback. Luma never sends play commands. |
| No new media player | REUSE | `Request::WebPlayer` (Luma's own) | None | Nuvio uses the TV's installed Nuvio app, not Luma's web player. No new player code. |
| No synthetic keyboard events | REUSE | Design decision | None | No keyboard injection code exists in Luma; none added. |
| No account/profile parameters | REUSE | Design decision | None | `nuvio_launch_params()` sends only `contentTarget`. No account, profile, token, or streaming URL fields. |
| Translations | ADAPT | `assets/messages.json` pattern | `assets/messages.json` | `nuvioNotInstalled` added in 5 locales following the existing `appOpenError` pattern. |
| Tests | CREATE | `src/tests.rs` test module pattern | `src/tests.rs` | New `#[cfg(feature = "nuvio")] mod nuvio` with 8 tests — no existing test covers Nuvio. |

### Files changed in Phase 1 (6 files)

| File | Change type | Feature-gated? |
|---|---|---|
| `Cargo.toml` | ADAPT (add feature) | N/A (feature definition) |
| `src/platform.rs` | ADAPT + CREATE | Yes (`#[cfg(feature = "nuvio")]`) |
| `src/state.rs` | ADAPT + CREATE | Yes (`#[cfg(feature = "nuvio")]`) |
| `src/main.rs` | ADAPT + CREATE | Yes (`#[cfg(feature = "nuvio")]`) |
| `assets/messages.json` | ADAPT | No (message always present, only shown when feature enabled) |
| `src/tests.rs` | CREATE | Yes (`#[cfg(feature = "nuvio")]`) |

### Files NOT changed (explicitly preserved)

`src/stacks.rs`, `src/stacks_view.rs`, `src/view.rs`, `src/media.rs`, `src/app_artwork.rs`, `src/jellyfin.rs`, `src/plex.rs`, `src/moonlight.rs`, `src/renderer.rs`, `src/motion.rs`, `src/widgets.rs`, `src/smart_home.rs`.

---

## Phase 2 — Continue Watching consumer (future, BLOCKED on producer contract)

| Nuvio capability | Classification | Existing owner | Files to change | Rationale |
|---|---|---|---|---|
| Continue Watching feed | CREATE (consumer only) | `stacks.rs` source registry | `src/stacks.rs`, `src/main.rs`, `src/nuvio.rs` (new) | No Nuvio producer API exists. Consumer interface follows Jellyfin/Plex `Service` pattern (worker thread, Command/Response, `Response::Items`). |
| Stack source `"nuvio"` | ADAPT | `stacks.rs::SOURCES` | `src/stacks.rs` | Add `"nuvio"` to `SOURCES` array; `has_library("nuvio")` → true; `collection_choices("nuvio")` returns future collections. |
| Stack card rendering | REUSE | `stacks_view.rs` | None | Existing `StackItem` poster rendering is source-agnostic. |
| Continue Watching → detail launch | REUSE | `Effect::NuvioLaunch` (Phase 1) | None | Phase 1 launch path already handles `contentTarget`; stack cards just need to produce the target. |
| Poster/backdrop caching | REUSE | `media::download_as()`, `app_artwork.rs` | None | Existing bounded download and cache patterns apply. |
| Profile isolation | CREATE | None | `src/nuvio.rs` (new) | No existing component handles profile-scoped Nuvio data. Must be designed when producer contract is authorized. |
| Async cancellation | CREATE | None | `src/nuvio.rs` (new) | Cancellation token pattern needed; no existing Nuvio-specific cancellation. |
| Loading/empty states | REUSE | `stacks_view.rs` (empty rows skipped) | None | `visible_rows()` in `stacks.rs` already skips empty rows; loading state exists via `state.loading`. |

**Blocked:** No Nuvio producer API exists in this repository. Consumer-side interface can be designed and tested with synthetic fixtures, but no producer integration can be implemented without authorization.

---

## Phase 3 — First-class Home row (future, BLOCKED on Phase 2)

| Nuvio capability | Classification | Existing owner | Files to change | Rationale |
|---|---|---|---|---|
| Home row rendering | REUSE | `stacks_view.rs` | None | `home_stacks()` renders any source in `SOURCES` generically. |
| Row navigation | REUSE | `state.direction()` | None | `Target::StackCard` navigation is source-agnostic. |
| Animated focus | REUSE | `src/motion.rs`, `state.focus_pop()` | None | Existing focus animation applies to all stack cards. |
| Reduced-motion fallback | REUSE | `state.preferences.reduced_motion` | None | Already handled in `tile()` and stack card rendering. |
| Artwork caching | REUSE | `media.rs`, `app_artwork.rs` | None | Existing cache patterns apply. |

---

## Decision rule: when to CREATE vs. REUSE

1. **REUSE first**: If an existing component (platform worker, state effect, stacks registry, view renderer) can handle the requirement with no or minimal changes, reuse it.
2. **ADAPT second**: If an existing component needs a small, bounded change (new variant, new constant, new arm), adapt it.
3. **CREATE third**: Only when no existing owner can satisfy the requirement (e.g., `validate_nuvio_target()`, new test module).
4. **REJECT explicitly**: Never duplicate Nuvio playback, account state, or create an independent UI framework.

**Justification for every CREATE in Phase 1:**
- `validate_nuvio_target()`: No existing function validates `nuvio://tmdb/` URLs. `valid_app_id()` validates app IDs, not content targets.
- `nuvio_launch_params()`: No existing function builds the Nuvio-specific `{"id": ..., "params": {"contentTarget": ...}}` payload.
- `mod nuvio` tests: No existing test module covers Nuvio launch validation or worker routing.