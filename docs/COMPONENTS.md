# Component Specifications — Nuvio Integration

Each component lists: what it does, how it behaves, how it connects, and whether it changes for Nuvio Phase 1.

## 1. Platform launch worker — `src/platform.rs`

### What it does

Runs all blocking platform/Luna work on a dedicated worker thread, never in the SDL/UI thread. Receives `Request` variants over an `mpsc` channel, performs LS2 calls to TV services, and sends `Response` back over a separate channel.

### How it behaves

- `webos == true`: real `luna://com.webos.applicationManager/launch` calls via `luna-service2` FFI bindings (`src/luna.rs`).
- `webos == false` (desktop): returns `Ok(())` without calling TV services.
- 6500ms timeout per Luna call with cancellation.
- `checked_response()` validates `returnValue == true` from TV replies.
- Error text is truncated to 240 chars and logged via `eprintln!`.

### How it connects

- `main.rs` calls `platform.send(Request::...)` from the effects dispatcher.
- `main.rs` polls `platform.receiver` for `Response` variants in the main run loop.

### Phase 1 changes

- Added `Request::NuvioLaunch { content_target: String }` (`#[cfg(feature = "nuvio")]`).
- Added `validate_nuvio_target()` — accepts only `nuvio://tmdb/movie/<digits>` and `nuvio://tmdb/tv/<digits>`.
- Added `nuvio_launch_params()` — builds `{"id": NUVIO_APP_ID, "params": {"contentTarget": ...}}`.
- Added `NUVIO_APP_ID` and `NUVIO_NOT_INSTALLED` constants (`#[cfg(feature = "nuvio")]`).
- Worker arm: validates target first; invalid targets fail without any TV call. Valid targets call launch; on error, `getAppInfo` preflight distinguishes absent-app from other errors.

### Default build impact

None — all Nuvio code is `#[cfg(feature = "nuvio")]` and `nuvio` is not in `default`.

---

## 2. Home state and navigation — `src/state.rs`

### What it does

Single owner of all UI state, navigation, focus, and effect production. `State` holds `page`, `focus`, `stack_items`, `launching`, `movie_cache`, `playback_progress`, and all other UI state.

### How it behaves

- `activate(target) -> Vec<Effect>` — maps focus targets to effects.
- `direction(direction, controls) -> Vec<Effect>` — D-pad navigation.
- `back() -> Vec<Effect>` — Back precedence chain.
- `focus_level(target)` / `focus_pop(target)` — tweened focus values for animation.
- `launching` flag prevents duplicate concurrent launches.
- Focus changes restart focus tweens for animation.

### How it connects

- `main.rs` calls `state.activate()`, `state.direction()`, `state.back()` in response to remote input.
- Effects are consumed by `main.rs effects()` which sends Platform requests.

### Phase 1 changes

- Added `Effect::NuvioLaunch { content_target: String }` (`#[cfg(feature = "nuvio")]`).
- Added `Target::NuvioLaunch` variant (`#[cfg(feature = "nuvio")]`).
- `activate()` arm: `Target::NuvioLaunch(ref content_target) if !self.launching` → `Effect::NuvioLaunch`. Focus is NOT moved.

### Default build impact

None — all Nuvio code is feature-gated.

---

## 3. Effect dispatch — `src/main.rs`

### What it does

`effects()` consumes `Vec<Effect>` produced by `state.activate()`/`state.direction()`/`state.back()` and dispatches them: sends Platform requests, weather commands, Home Assistant commands, media commands, etc.

### How it behaves

- `Effect::Launch(id)` → `platform.send(Request::Launch(id))` (webOS) or desktop preview notice.
- `Effect::NuvioLaunch { content_target }` → `platform.send(Request::NuvioLaunch { content_target })` (webOS) or desktop preview notice.
- `!state.launching` guard checked before sending any launch.
- `run()` main loop polls `platform.receiver` for `Response::Launched`, sets `state.launching = false`, shows error or success.

### How it connects

- Receives effects from `state.rs`.
- Sends requests to `platform.rs`.
- Receives responses from `platform.rs`.

### Phase 1 changes

- Added `Effect::NuvioLaunch` arm in `effects()`.
- Added `NUVIO_NOT_INSTALLED` error handling in `Response::Launched` match → `state.notify("Nuvio isn't installed.")` translated.

### Default build impact

None — all Nuvio code is feature-gated.

---

## 4. Stack source registry — `src/stacks.rs`

### What it does

Defines `StackConfig` (name, source, collection, shape, show) and `StackItem` (title, poster, id). Maintains `SOURCES` list and helper functions for row rendering.

### How it behaves

- `visible_rows(state)` filters stacks by `show == true` and non-empty items.
- `row_shown(state, row)` caps at `HOME_ROW_MAX = 20`.
- `has_library(source)` → true for moonlight/jellyfin/plex (adds "View Library" card).
- `collection_choices(state, stack)` returns per-source collections.
- `source_label(source)` returns display name for source pill.

### How it connects

- `state.preferences.stacks: Vec<StackConfig>` holds user configuration.
- `state.stack_items: Vec<Vec<StackItem>>` holds fetched row contents.
- `stacks_view.rs` calls `rows(state)` to render.

### Phase 1 changes

None. Phase 1 does not add a Nuvio stack row.

### Phase 2+ (future, blocked)

- Add `"nuvio"` to `SOURCES`.
- `has_library("nuvio")` → true.
- `collection_choices("nuvio")` returns `["continue-watching", "watchlist", "library"]` when producer contract exists.

---

## 5. Stack card rendering — `src/stacks_view.rs`

### What it does

Renders Home stack rows: section titles, source labels, poster cards, library cards, focus rings, zoom, sheen, ambient movement.

### How it behaves

- Each `StackItem` poster drawn as `Draw::TintedImage(path, rect, radius, ...)`.
- Missing poster → colored placeholder with title text.
- Library card → grey card with grid icon and "View Library" text.
- Focus zoom: `1. + 0.06 * pop`; shadow scales with focus level.
- Cards off-screen are not drawn.
- Entrance stagger per row.

### How it connects

- Called from `view.rs` home page rendering.
- Receives `state.stack_items`, `state.preferences.stacks`, `state.focus` for focus level.

### Phase 1 changes

None.

---

## 6. App tile rendering — `src/view.rs`

### What it does

Renders app tiles in the Apps grid and Home favorites. `tile()` function handles artwork, focus, zoom, shadow, entrance animation.

### How it behaves

- Branding logo or app icon from `app_artwork::Service`.
- Focus zoom: `1. + 0.07 * pop`; reduced-motion skips animation.
- Entrance cascade: `motion::cascade_progress()` per card on tab entry.
- Cards off-screen (y < MAIN_TOP or y > 1054) are not submitted.

### How it connects

- `state.focus == Target::App(app.id)` determines focused tile.
- `app.icon: Option<Source>` points to artwork source.

### Phase 1 changes

None.

---

## 7. Shared media types — `src/media.rs`

### What it does

Shared `Detail`, `PlayRequest`, `Episode`, `LibraryPage` types used by Jellyfin and Plex. Also `download_as()` (bounded 4MB HTTP download), `poster_backdrop()` (16:9 blurred crop), `ThumbService` (background still downloader).

### How it behaves

- `download_as()` limits response body to 4MB, caches to disk.
- `poster_backdrop()` crops upper 16:9 of poster, blurs, saves to cache.
- `ThumbService` is a single background worker thread for episode stills.

### How it connects

- Jellyfin and Plex `Service` workers use these types and functions.
- `state.movie_cache: HashMap<i64, Detail>` caches fetched details.

### Phase 1 changes

None. Nuvio titles launch into Nuvio's own app; Luma does not render Nuvio media details.

---

## 8. Installed app artwork — `src/app_artwork.rs`

### What it does

Discovers, decodes, and caches installed app icons from TV filesystem. Worker thread with memory + disk cache.

### How it behaves

- `Source { id, directory, large_icon, icon, version }` — version changes invalidate cache on app update.
- `MAX_FILE = 512KB` per icon; `CACHE_BYTES = 48MB`; `CACHE_ENTRIES = 256`; `DISK_ARTWORK_MAX = 768KB`.
- Disk cache keys are FNV-1a hashes of serialized `Source`.
- TV builds read from `/usr/palm/applications`, `/media/developer/apps/...`, `/media/cryptofs/apps/...`.

### How it connects

- `platform.rs normalize_apps()` sets `app.icon = Some(Source::new(id, entry))`.
- `view.rs tile()` looks up `assets.artwork.get(source)`.

### Phase 1 changes

None.

---

## 9. Translations — `src/i18n.rs` + `assets/messages.json`

### What it does

5-language message catalog (en/de/es/zh/pt). `Language::t(key)` looks up translated string. `Language::format(key, values)` replaces `{name}` placeholders.

### How it behaves

- All 5 languages required for every message (enforced by unit test `every_message_has_all_languages_and_no_empty_values`).
- Placeholders must match across languages (enforced by test).

### Phase 1 changes

Added `nuvioNotInstalled` in all 5 locales:

- en: "Nuvio isn't installed."
- de: "Nuvio ist nicht installiert."
- es: "Nuvio no está instalado."
- zh: "未安装 Nuvio。"
- pt: "O Nuvio não está instalado."

### Default build impact

Message is always present in the JSON catalog; only displayed when `nuvio` feature is enabled and `NUVIO_NOT_INSTALLED` error occurs.

---

## 10. Tests — `src/tests.rs`

### What it does

Unit tests for model, platform, state, i18n, artwork. Uses `demo_inventory()` for test data. `ready()` helper creates a `State` with demo inventory.

### How it behaves

- Tests run with `cargo test`.
- `#[cfg(feature = "nuvio")]` gates Nuvio-specific tests.
- `Platform::new(webos)` creates a real platform worker for desktop testing.

### Phase 1 changes

Added `#[cfg(feature = "nuvio")] mod nuvio` with 8 tests:

1. `nuvio_target_validates_movie_and_series_identifiers` — valid targets
2. `nuvio_target_rejects_malformed_targets` — 11 invalid cases
3. `nuvio_app_id_is_fixed_and_valid` — `space.nuvio.webos` passes `valid_app_id()`
4. `nuvio_launch_params_match_the_contract` — payload shape
5. `nuvio_launch_routes_through_the_platform_worker` — real `Platform::new(true)` routing
6. `nuvio_invalid_target_is_rejected_before_reaching_tv_services` — pre-validation
7. `nuvio_duplicate_launch_is_blocked_while_launching` — `launching == true` blocks
8. `nuvio_launch_keeps_focus_for_back_restoration` — focus unchanged

---

## 11. Renderer — `src/renderer.rs` (108,741 lines)

### What it does

OpenGL rendering thread. SDL window, GL context, shader programs, draw commands, texture upload, frame pacing.

### How it behaves

- Consumes `Draw` commands from `Scene`.
- Damage tracking and partial redraw.
- Vector geometry tessellation.
- Font atlas and glyph caching.

### Phase 1 changes

None.

---

## 12. Motion system — `src/motion.rs`

### What it does

Focus animation springs, entrance cascades, card rise, sheen, kinetic scrolling.

### How it behaves

- `FOCUS_POP`, `FOCUS_SHEEN`, `CARD_RISE` constants.
- `cascade_progress()` for entrance stagger.
- Reduced-motion aware: returns 1.0 (instant) when `preferences.reduced_motion`.

### Phase 1 changes

None.

---

## Component connection summary (Phase 1)

```
User action
    |
    v
state.activate()                    [src/state.rs]  -- Target::NuvioLaunch (NEW)
    |
    v
Effect::NuvioLaunch                 [src/state.rs]  -- NEW variant, focus preserved
    |
    v
main.rs effects()                   [src/main.rs]   -- NEW arm, platform.send()
    |
    v
platform.send(Request::NuvioLaunch) [src/platform.rs] -- NEW variant
    |
    v
validate_nuvio_target()             [src/platform.rs] -- NEW, pre-validation
    |
    v
luna://com.webos.applicationManager/launch  [src/platform.rs, src/luna.rs]
    |
    v
TV response → Response::Launched  [src/platform.rs]
    |
    v
main.rs run() response handling     [src/main.rs]   -- state.launching = false, notice
    |
    v
Renderer redraw                     [src/renderer.rs] -- no change
```

**No new component created.** Every Phase 1 addition is a variant, arm, function, or constant inside an existing owner file. No new file (other than docs) was created for the implementation.
