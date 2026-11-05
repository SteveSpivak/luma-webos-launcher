# Integration Audit — Reverse Engineering of Existing Luma Integrations

Traced end-to-end from actual source code. Each integration follows the pattern:
**Configuration → Source selection → Background work → Data normalization → State → Home card → Focus → Enter → Launch/Playback → Back → Cleanup.**

## 1. Jellyfin — `src/jellyfin.rs` (1,529 lines)

### Configuration
- `Preferences.jellyfin: JellyfinLink` — fields: `server`, `server_name`, `user_id`, `user_name`, `token`, `device_id`.
- `JellyfinLink::linked()` returns true when `token` and `server` are non-empty.
- Token is never logged (documented in module comment).
- Saved per-install `device_id` so Jellyfin lists Luma as its own device.

### Source selection
- Settings › Stacks → `StackConfig { source: "jellyfin", collection, shape, show }`.
- Collections: `resume` (Continue watching), `nextup` (Next up), `latest` (Recently added), `albums` (Recently added albums).
- Music collections (`albums` or `music:*`) use `CardShape::Square`; others use `Poster`.

### Background work
- `jellyfin::Service` — worker thread with `Mutex<mpsc::Sender<Command>>` and `Mutex<mpsc::Receiver<Response>>`.
- `Command::Fetch(link, stacks)` → `fetch()` function iterates collections, calls Jellyfin REST endpoints (`/UserItems/Resume`, `/Shows/NextUp`, `/Items`), downloads posters into cache dir (`/media/developer/com.denisefremov.luma/posters` or temp dir), sends `Response::Items(index, Vec<StackItem>)`.
- Bounded: `HOME_ROW_MAX = 20` cards per row; cached posters show immediately, rest arrive in one more update.
- `ATTEMPT` static counter for Quick Connect correlation.

### Data normalization
- `card_id(item: &str) -> i64` — FNV-1a hash of Jellyfin GUID, with `CARD_TAG = 1 << 52` bit set so media source ids are distinguishable.
- `CARD_IDS: Mutex<BTreeMap<i64, String>>` preserves id↔GUID mapping across runs.
- `ALBUM_IDS: Mutex<BTreeSet<i64>>` marks album cards; `is_album(id)` checks it.
- `owns(id: i64)` — true when `id & CARD_TAG != 0` and present in `CARD_IDS`.

### State
- `main.rs:jellyfin_tick()` — `Response::Items(index, items)` → `state.stack_items[index] = items`; `Response::Linked` → saves prefs, creates stacks, calls `stacks_refresh()`.
- `state.stack_items: Vec<Vec<StackItem>>` — indexed by stack position.

### Home card
- `stacks_view.rs:home_stacks()` — renders `StackItem` posters as `Draw::TintedImage`, control target `Target::StackCard(row, index)`, grey "View Library" card at row end when `has_library("jellyfin") == true`.
- `source_label("jellyfin")` = "Jellyfin".

### Focus
- `state.direction()` navigates `Target::StackCard(row, index)` within row (Left/Right) and between rows (Up/Down).
- `state.stack_scroll: (row, offset, goal)` tracks horizontal scroll per row.
- `state.focus_level(&target)` and `state.focus_pop(&target)` provide tweened focus for animation.

### Enter
- `state.activate()` → `Target::StackCard` → `open_movie(item, pool, Target::StackCard(row, index))` (defined in `src/state.rs`, calls into `movie.rs` logic).
- Creates `MovieCard { id, title, poster, detail: None, ... }`, `change_focus(Target::MoviePlay)`, `dirty = true`.
- Returns `Effect::MediaDetails(id)`.

### Launch / playback
- `main.rs effects()` → `Effect::MediaDetails(id)` → `jellyfin_service().send(Command::Details(link, id))`.
- Worker fetches detail → `Response::Details(Box<Detail>)` → `state.media_detail()` → `state.movie_details()` renders title card.
- OK on `Target::MoviePlay` → `Effect::MediaPlay(request)` → `jellyfin::Command::Play` → `player::OpenRequest` → `open_player()`.
- `open_player()` on webOS → `state.launching = true`, `state.web_player_item = item_id`, `platform.send(Request::WebPlayer(web_player_params))`.
- `web_player_params()` builds JSON with signed URL, title, source, subtitles, qualities — never logged.

### Back
- `state.back()` → movie close → saves `preferences.playback_progress[id] = position_ms`, clears `state.movie`, focus → `Target::MoviePlay`.

### Cleanup
- `movie_cache: HashMap<i64, Detail>` retains detail across opens.
- Posters cached on disk in cache directory.

### Tests
- No Jellyfin-specific unit tests found in `src/tests.rs` (network-dependent, integration-level only).

---

## 2. Plex — `src/plex.rs` (946 lines)

Identical architecture to Jellyfin with these differences:
- `PlexLink`: `client_id`, `account_token`, `user_name`, `server_name`, `server_id`, `server_uri`, `server_token`.
- `PlexLink::linked()` true when `server_token` and `server_uri` non-empty.
- Sign-in via plex.tv PIN (4-letter code) + QR, polled until approved.
- Collections: `ondeck` (On Deck), `recent` (Recently added).
- `plex::Service` worker thread, same Command/Response pattern.
- `plex_tick()` in `main.rs` handles responses identically to Jellyfin.
- Same `open_movie` → `open_player` → `Request::WebPlayer` flow.
- Same `StackItem` type, same `stacks_view.rs` rendering.

---

## 3. Moonlight — `src/moonlight.rs` (1,911 lines)

Different payload: games, not media titles.

### Configuration
- `MoonlightLink`: `host_name`, `host_uuid`, `address`, `mac`, `https_port`, certs/keys, `paired`.
- `GameLibrary`: `played: Vec<(i64, u64)>`, `first_seen: BTreeMap<i64, u64>`, `favorites: Vec<i64>`.
- `record_play(id)` — newest first, truncates to 50.

### Background work
- `moonlight::Service` — UDP broadcast discovery, TCP pairing, RSA authentication, TLS.
- `Command::Fetch(link)` → `fetch()` → Apollo game list → `StackItem` with `id` = game id, `poster` cached.

### State
- `state.moonlight_games`, `state.moonlight_online`, `state.moonlight_status`.

### Home card
- `stacks_view.rs` renders game posters; `has_library("moonlight") == true` adds "View Library" card.
- `source_label("moonlight")` = "Moonlight".

### Enter
- `Target::StackCard` for moonlight → `GameCard::new()`, `focus = Target::GamePlay`, `Effect::GameInfo(id, title)`.
- `Target::GamePlay` → `Effect::MoonlightPlay(id)` → `Request::MoonlightLaunch(link, id)` → `Request::Launch("com.limelight.webos")`.

### Back
- `state.back()` → `close_game()` → `Effect::MoonlightQuit`.

### Tests
- `moonlight.rs` has inline tests: `assert!(matches!(effects.as_slice(), [Effect::MoonlightPair(_)]))`, etc.

---

## 4. Home source registry — `src/stacks.rs` (259 lines)

### Source registry
```rust
pub const SOURCES: [(&str, &str, bool); 3] = [
    ("moonlight", "Moonlight", true),
    ("jellyfin", "Jellyfin", true),
    ("plex", "Plex", true),
];
```

### StackConfig
```rust
pub struct StackConfig {
    pub name: String,
    pub source: String,       // "moonlight", "jellyfin", "plex"
    pub collection: String,   // "fresh", "popular", "continue", "history", "bookmark:<id>", "pick:<id>"
    pub list_title: String,
    pub shape: CardShape,     // Poster, Square, Wide
    pub show: bool,
}
```

### StackItem
```rust
pub struct StackItem {
    pub title: String,
    pub poster: Option<String>,  // cached poster file path
    pub id: i64,                 // 0 for placeholders
}
```

### Key functions
- `has_library(source)` → true for moonlight/jellyfin/plex (adds "View Library" card).
- `collection_choices(state, stack)` → per-source collections (moonlight: games; jellyfin: resume/nextup/latest/albums + views; plex: ondeck/recent + views).
- `row_title(stack)` → display title for a row.
- `row_shown(state, row)` → caps at `HOME_ROW_MAX = 20`.
- `row_pitch(state, row)` → per-row card pitch.
- `compact(source)` → true for moonlight/jellyfin/plex (sign-out row instead of type row).

---

## 5. Shared media presentation — `src/media.rs` (188 lines)

### Types
- `PlayRequest { id, episode, quality, subtitle }`
- `Episode { season, number, title, minutes, progress, watched, thumb_url, thumb }`
- `Detail { id, serial, title, year, minutes, genres, countries, plot, director, cast, imdb, kinopoisk, tags, poster, backdrop, audio, subtitles, qualities, trailer, seasons, episodes, next }`
- `LibraryPage { items: Vec<(i64, String, String)>, pages, total }`

### Functions
- `download_as(agent, cache, name, url) -> Option<String>` — bounded 4MB HTTP download to cache, returns cached path.
- `poster_backdrop(cache, name, poster)` — 16:9 blurred crop from poster upper portion.
- `season_stills(agent, cache, detail)` — downloads episode stills.
- `ThumbService` — background episode still downloader (single worker thread).
- `thumbs_request(id, list)` / `thumbs_poll()` — async still delivery.

---

## 6. Home state and effects — `src/state.rs` (216,899 lines)

### Single owner of all navigation/state
`State` contains:
- `page: Page` (Home, Apps, SmartHome, Settings)
- `focus: Target` — current focus target
- `stack_items: Vec<Vec<StackItem>>` — per-stack row contents
- `launching: bool` — prevents duplicate concurrent launches
- `movie_cache: HashMap<i64, Detail>` — prefetched/cached media details
- `movie_prefetch: (Option<(Target, Instant)>, HashSet<i64>)` — dwell-based prefetch
- `movie_prefetch_busy: Option<(i64, Instant)>` — one-at-a-time prefetch
- `playback_progress: BTreeMap<String, u64>` — saved positions

### Effects enum
`Effect::Launch`, `Effect::Refresh`, `Effect::Reload`, `Effect::Quit`, `Effect::MoonlightPlay`, `Effect::MediaPlay`, `Effect::MediaDetails`, `Effect::NuvioLaunch` (NEW), etc.

### Key methods
- `activate()` — dispatches `Target::*` → `Vec<Effect>`
- `direction(direction, controls)` — D-pad navigation, returns `Vec<Effect>`
- `back()` — Back precedence, returns `Vec<Effect>`
- `focus_level(target)` / `focus_pop(target)` — tweened focus for animation
- `movie_prefetch()` — dwell-based detail prefetch (PREFETCH_DWELL threshold)
- `change_focus(target)` — focus change with tween restart

---

## 7. Card rendering — `src/view.rs` and `src/stacks_view.rs`

### `src/stacks_view.rs` — `home_stacks()`
- Iterates visible stacks (non-empty, show=true)
- Draws section title + source label
- Renders each `StackItem` poster as `Draw::TintedImage` with focus zoom/sheen
- Grey "View Library" card at row end when `has_library()`
- Cards clipped by screen bottom, off-screen rows not drawn but scrollable
- `library_card()` — grey card with grid icon and "View Library" text

### `src/view.rs` — `tile()`
- App tile rendering for Apps grid
- Branding logo or app icon artwork
- Focus level tween, zoom (1 + 0.07 * pop), shadow, accent glow
- Entrance cascade animation (reduced-motion aware)
- `TILE_RADIUS = 26.0`

### Focus targets
- `Target::StackCard(row, index)` — stack cards
- `Target::App(id)` — app tiles
- `Target::MoviePlay`, `Target::MovieBack`, etc. — movie card targets
- Catch-all `_ => {}` at end of `activate()` match ensures exhaustiveness

---

## 8. Platform launching — `src/platform.rs` (665 lines)

### Platform worker
- One blocking worker thread, never in SDL/UI thread
- `mpsc::Sender<Request>` / `mpsc::Receiver<Response>`
- `webos: bool` — TV builds call real Luna services; desktop returns `Ok(())`

### Request variants
- `Refresh` — app inventory + input status
- `Launch(id)` — `luna://com.webos.applicationManager/launch {"id": id}`
- `CloseApp(id)` — `luna://com.webos.service.applicationmanager/closeByAppId`
- `WebPlayer(params)` — `com.denisefremov.luma.player` with signed URLs
- `MoonlightLaunch(link, id)` — `com.limelight.webos`
- `NuvioLaunch { content_target }` (NEW, cfg nuvio) — Nuvio deep-link launch
- `Root(change)` — root features (wake, home auto launch)
- `Signals` — HDMI signal info

### Response variants
- `Inventory(Result<(Inventory, Option<String>), String>)`
- `Launched(Result<(), String>)` — used by Launch, WebPlayer, MoonlightLaunch, NuvioLaunch
- `Root(Result<Option<RootStatus>, String>)`
- `Signals(Vec<(u8, bool)>)`

### Validation
- `valid_app_id(id)` — non-empty, ≤128 chars, dot/underscore/dash-separated alphanumeric parts
- `player_not_installed(error)` — classifies "not installed"/"not found"/etc. from TV error text
- `app_not_installed(error)` (NEW) — shared classification used by Nuvio and WebPlayer

### Nuvio-specific additions (Phase 1)
- `NUVIO_APP_ID = "space.nuvio.webos"` [cfg(nuvio)]
- `NUVIO_NOT_INSTALLED = "Nuvio is not installed"` [cfg(nuvio)]
- `validate_nuvio_target(target) -> Result<String, String>` [cfg(nuvio)] — accepts only `nuvio://tmdb/movie/<digits>` and `nuvio://tmdb/tv/<digits>`
- `nuvio_launch_params(content_target) -> Value` [cfg(nuvio)] — `{"id": NUVIO_APP_ID, "params": {"contentTarget": target}}`
- Worker arm: validates target, then calls launch; on error, `getAppInfo` preflight to distinguish absent-app from other errors

---

## 9. Media and artwork owners — `src/app_artwork.rs`

### Source
```rust
pub struct Source {
    pub id: String,
    pub directory: Option<PathBuf>,
    pub large_icon: Option<String>,
    pub icon: Option<String>,
    pub version: Option<String>,
}
```

### Service
- Worker thread decodes installed app icons from TV filesystem roots
- Memory cache: `CACHE_BYTES = 48MB`, `CACHE_ENTRIES = 256`
- Disk cache: `DISK_ARTWORK_MAX = 768KB`, FNV hash keys
- `MAX_FILE = 512KB` per icon
- Used for app icons in Apps grid, NOT for stack media posters

---

## 10. Cross-integration summary

| Aspect | Jellyfin | Plex | Moonlight | Nuvio (Phase 1) |
|---|---|---|---|---|
| Backend service | `jellyfin::Service` | `plex::Service` | `moonlight::Service` | Platform worker only |
| Link stored in Preferences | `jellyfin: JellyfinLink` | `plex: PlexLink` | `moonlight: MoonlightLink` | None (no account) |
| Stack source | `"jellyfin"` | `"plex"` | `"moonlight"` | Not yet (Phase 2) |
| Stack items | `Vec<StackItem>` | `Vec<StackItem>` | `Vec<StackItem>` | Not yet (Phase 2) |
| Card rendering | `stacks_view.rs` | `stacks_view.rs` | `stacks_view.rs` | Reuse `stacks_view.rs` |
| Enter action | `open_movie()` → `Effect::MediaDetails` | `open_movie()` → `Effect::MediaDetails` | `Effect::MoonlightPlay` | `Effect::NuvioLaunch` |
| Launch mechanism | `Request::WebPlayer` | `Request::WebPlayer` | `Request::Launch("com.limelight.webos")` | `Request::NuvioLaunch` |
| Playback owner | Nuvio/Jellyfin server | Nuvio/Plex server | Sunshine PC | Nuvio app (Luma only launches) |
| Account data in Luma | Token, server | Token, server | Host certs, paired | None |
| Back behavior | Save progress, close movie | Save progress, close movie | `Effect::MoonlightQuit` | Focus preserved, no state change |
| Tests | Integration only | Integration only | Inline unit tests | 8 unit tests (Phase 1) |

## 11. What Nuvio Phase 1 reuses vs. creates

**REUSE (no changes needed):**
- `platform.rs` worker thread pattern
- `Request::Launch` / `Response::Launched` pattern
- `state.launching` duplicate guard
- `state.activate()` / `state.back()` focus preservation
- `stacks_view.rs` card rendering (Phase 2+)
- `assets/messages.json` translation pattern
- `src/tests.rs` test module pattern

**ADAPT (minimal changes):**
- `platform.rs`: add `Request::NuvioLaunch`, `validate_nuvio_target()`, `nuvio_launch_params()`, `NUVIO_APP_ID`, `NUVIO_NOT_INSTALLED`
- `state.rs`: add `Effect::NuvioLaunch`, `Target::NuvioLaunch`, `activate()` arm
- `main.rs`: add `effects()` arm, error notice handling
- `assets/messages.json`: add `nuvioNotInstalled`

**CREATE (new code):**
- Validation logic `validate_nuvio_target()`
- Launch params builder `nuvio_launch_params()`
- Test module `mod nuvio` in `src/tests.rs`

**REJECT (explicitly not done):**
- No Nuvio playback engine
- No Nuvio account/profile storage
- No independent Nuvio UI framework
- No new API server
- No Continue Watching feed (Phase 2, blocked on producer contract)