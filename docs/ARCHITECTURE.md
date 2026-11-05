# Architecture — Source Ownership Map and Dependency Graph

All observations below are traced from actual source files in `src/`, not inferred from file names.

## 1. High-level data flow

```
Remote input (SDL)
    |
    v
State.direction() / State.activate()      [src/state.rs]
    |  (produces Effect)
    v
Main.effects()                            [src/main.rs]
    |  (consumes Effect, sends Platform Request)
    v
Platform worker thread                    [src/platform.rs]
    |  (LS2 luna-send to TV services)
    v
webOS applicationManager / Luna services
    |
    v
TV response (Response::Launched)
    |
    v
Main.run() response handling              [src/main.rs]
    |  (state.launching = false, notify)
    v
State (focus preserved, dirty = true)
    |
    v
Renderer.draw()                           [src/renderer.rs]
```

## 2. Source ownership map

| Component | Owner file(s) | Responsibility |
|---|---|---|
| Platform launch worker | `src/platform.rs` | One blocking worker thread, never in SDL/UI thread. LS2 calls to `applicationManager/launch`, `getAppInfo`, inventory services. |
| App launch (generic) | `src/platform.rs` `Request::Launch` | `luna://com.webos.applicationManager/launch {"id": id}` with `valid_app_id()` validation. |
| Web player launch | `src/platform.rs` `Request::WebPlayer` | Launch `com.denisefremov.luma.player` with signed URLs/tokens. Never logged. |
| Moonlight launch | `src/platform.rs` `Request::MoonlightLaunch` | Launch `com.limelight.webos` with moonlight link params. |
| Nuvio launch (NEW) | `src/platform.rs` `Request::NuvioLaunch` | `luna://com.webos.applicationManager/launch {"id": "space.nuvio.webos", "params": {"contentTarget": ...}}`. Feature-gated. |
| Home state & navigation | `src/state.rs` | Single owner of `State`, `launching` flag, focus, `movie_cache`, `stack_items`, `activate()`, `direction()`, `back()`. |
| Effects | `src/state.rs` `enum Effect` | `Launch`, `Refresh`, `Reload`, `Quit`, `MoonlightPlay`, `MediaPlay`, `MediaDetails`, `NuvioLaunch` (NEW), etc. |
| Effect dispatch | `src/main.rs` `effects()` | Matches `Effect` variants, sends `Platform.Request`, handles responses. |
| Launch response handling | `src/main.rs` `run()` | `Response::Launched` → `state.launching = false`, error notice or success. |
| Stack source registry | `src/stacks.rs` | `StackConfig`, `StackItem`, `SOURCES` list, `has_library()`, `collection_choices()`, `row_shown()`, `row_pitch()`. |
| Stack card rendering | `src/stacks_view.rs` | `home_stacks()` draws poster cards + library card, focus rings, sheen, zoom. |
| App tile rendering | `src/view.rs` `tile()` | App icons, captions, focus level, zoom, entrance animation. |
| Shared media types | `src/media.rs` | `Detail`, `PlayRequest`, `Episode`, `LibraryPage`, `download_as()`, `poster_backdrop()`, `ThumbService`. |
| Installed app artwork | `src/app_artwork.rs` | `Source`, disk/memory cache, decode worker, `MAX_FILE=512KB`, `CACHE_BYTES=48MB`. |
| Translations | `src/i18n.rs`, `assets/messages.json` | 5 languages (en/de/es/zh/pt), `t()` lookup, `format()` placeholder replacement. |
| Tests | `src/tests.rs` | Unit tests for model, platform, state, i18n, artwork. |

## 3. Existing integration dependency graphs

### Jellyfin (reference integration)

```
Preferences.jellyfin (JellyfinLink: server, token, user_id, device_id)
    |
    v
Settings › Stacks → StackConfig { source: "jellyfin", collection: "resume|nextup|latest|albums" }
    |
    v
jellyfin::Service worker thread (Command::Fetch)
    |
    v
HTTP GET /UserItems/Resume etc. (Jellyfin server)
    |
    v
card_id() FNV-1a hash of GUID -> i64 (CARD_TAG bit set)
    |
    v
Poster download to cache dir (media::download_as)
    |
    v
Response::Items(index, Vec<StackItem>)
    |
    v
main.rs jellyfin_tick() → state.stack_items[index] = items
    |
    v
stacks_view.rs home_stacks() renders StackItem posters
    |
    v
User focuses Target::StackCard(row, index)
    |
    v
User presses OK → state.activate()
    |
    v
open_movie(item, pool, Target::StackCard(row, index))
    |
    v
MovieCard created, focus → Target::MoviePlay, Effect::MediaDetails(id)
    |
    v
jellyfin::Command::Details → worker fetches detail → Response::Details
    |
    v
state.media_detail() → state.movie_details() renders title card
    |
    v
OK on Target::MoviePlay → Effect::MediaPlay(request)
    |
    v
jellyfin::Command::Play → OpenRequest → open_player()
    |
    v
platform.send(Request::WebPlayer(web_player_params))  [webOS]
    |  OR local playback session  [desktop]
    |
    v
Back → state.back() → saves playback_progress[id], clears movie
```

### Plex (reference integration)

Identical architecture to Jellyfin, with `PlexLink`, `plex::Service`, `plex_tick()`, `Response::Items`, same `open_movie` → `open_player` flow.

### Moonlight (reference integration)

Different payload: games, not media titles.
```
MoonlightLink → moonlight::Service → Command::Fetch → Apollo game list
    → StackItem (id = game id, poster cached)
    → Target::StackCard → GameCard → Target::GamePlay
    → Effect::MoonlightPlay(id) → Request::MoonlightLaunch(link, id)
    → Request::Launch("com.limelight.webos")
Back → Effect::MoonlightQuit
History in GameLibrary (played, first_seen, favorites)
```

## 4. Where Nuvio Phase 1 fits

Phase 1 is **launch-only**, shorter than the full media-card flow:

```
User action (e.g. OK on a future Nuvio stack card, or menu action)
    |
    v
state.activate() → Target::NuvioLaunch → Effect::NuvioLaunch { content_target }
    |  (focus NOT moved — preserved for Back restoration)
    |  (!self.launching guard blocks duplicates)
    v
main.rs effects() → platform.send(Request::NuvioLaunch { content_target })
    |
    v
Platform worker: validate_nuvio_target() rejects malformed before any TV call
    |
    v
luna://com.webos.applicationManager/launch {"id": "space.nuvio.webos", "params": {"contentTarget": "nuvio://tmdb/movie/603"}}
    |
    v
TV response → Response::Launched(Ok) → state.launching = false, dirty = true
    |  OR Response::Launched(Err(NUVIO_NOT_INSTALLED)) → translated notice
    v
Focus untouched → Back out of Nuvio returns to same focus
```

## 5. Where Nuvio Phase 2+ would fit (future, blocked on producer contract)

```
Nuvio producer (future, not in this repo) publishes Continue Watching
    |
    v
nuvio::Service (future, src/nuvio.rs) — read-only, profile-scoped, cancellation tokens
    |
    v
Response::Items(index, Vec<StackItem>) → state.stack_items[index]
    |
    v
stacks_view.rs renders Nuvio row (reuses existing card rendering)
    |
    v
Target::StackCard → activate() → Effect::NuvioLaunch → platform launch
```

No new rendering system, no new navigation engine — reuse `stacks_view.rs`, `state.direction()`, `state.activate()`.

## 6. File-level dependency graph (Phase 1 only)

```
Cargo.toml  (feature: nuvio = [], default off)
    |
    +-- src/platform.rs
    |       +-- NUVIO_APP_ID, NUVIO_NOT_INSTALLED  [cfg(nuvio)]
    |       +-- Request::NuvioLaunch               [cfg(nuvio)]
    |       +-- validate_nuvio_target()            [cfg(nuvio)]
    |       +-- nuvio_launch_params()              [cfg(nuvio)]
    |       +-- app_not_installed()                [shared with player_not_installed]
    |
    +-- src/state.rs
    |       +-- Effect::NuvioLaunch                [cfg(nuvio)]
    |       +-- Target::NuvioLaunch                [cfg(nuvio)]
    |       +-- activate() arm                     [cfg(nuvio)]
    |
    +-- src/main.rs
    |       +-- effects() arm for Effect::NuvioLaunch [cfg(nuvio)]
    |       +-- Response::Launched error handling  [cfg(nuvio)]
    |
    +-- assets/messages.json
    |       +-- nuvioNotInstalled (en/de/es/zh/pt)
    |
    +-- src/tests.rs
            +-- mod nuvio [cfg(feature = "nuvio")] — 8 tests
```

No changes to `stacks.rs`, `stacks_view.rs`, `media.rs`, `app_artwork.rs`, or `view.rs` in Phase 1.

## 7. Verification status

| Artifact | Status | Reason |
|---|---|---|
| Source inspection | Complete | All owner files read |
| Dependency graph | Source-backed | Traced from actual code |
| Native build | NOT RUN | No Rust toolchain in sandbox |
| `cargo test` | NOT RUN | No Rust toolchain |
| `cargo clippy -D warnings` | NOT RUN | No Rust toolchain |
| `cargo fmt --check` | NOT RUN | No Rust toolchain |
| Rollback | Documented | `git revert 6dc1886 3031417` or `git reset --hard 40994fc` |