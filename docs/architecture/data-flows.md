# Data Flows

Key end-to-end data flows traced through actual source code. Each flow shows: entry point → processing → state → rendering → exit/cleanup.

## Flow 1: Remote input → app launch (generic)

```
[Remote: OK on app tile]
        |
        v
state.activate()                              [src/state.rs]
        |
        +-- focus == Target::App(id) && !launching
        |       |
        |       v
        |   Effect::Launch(id)
        |       |
        |       v
        |   main.rs effects()                 [src/main.rs]
        |       |
        |       +-- platform.webos == true
        |       |       |
        |       |       v
        |       |   platform.send(Request::Launch(id))  [src/platform.rs]
        |       |       |
        |       |       v
        |       |   [Platform worker thread]
        |       |       |
        |       |   luna://com.webos.applicationManager/launch {"id": id}
        |       |       |
        |       |   TV reply → Response::Launched(Ok/Err)
        |       |       |
        |       |   state.launching = false
        |       |   Err → state.notify(appOpenError)
        |       |
        |       +-- platform.webos == false (desktop)
        |               |
        |               v
        |           state.notify(desktopPreview)
        |
        +-- state.launching == true (duplicate)
                |
                v
            activate() returns [] (blocked)
```

**Source owners:** `src/state.rs` (activate), `src/main.rs` (effects), `src/platform.rs` (worker)

---

## Flow 2: Stack card → media title → playback → Back

```
[Remote: OK on stack card (Target::StackCard)]
        |
        v
state.activate()                              [src/state.rs]
        |
        v
open_movie(item, pool, Target::StackCard)     [src/state.rs]
        |
        +-- MovieCard created, detail: None
        +-- focus → Target::MoviePlay
        +-- dirty = true
        +-- Effect::MediaDetails(id)
                |
                v
main.rs effects() → Effect::MediaDetails(id)  [src/main.rs]
        |
        v
jellyfin_service().send(Command::Details)     [src/jellyfin.rs]
        |
        v
[Worker: HTTP GET /Items/{id} → Detail JSON]
        |
        v
Response::Details(Box<Detail>)
        |
        v
state.media_detail() → state.movie_details()  [src/state.rs]
        |
        v
[Renderer draws title card: backdrop, cast, seasons, episodes]
        |
        v
[Remote: OK on Target::MoviePlay]
        |
        v
Effect::MediaPlay(request)
        |
        v
jellyfin_service().send(Command::Play)        [src/jellyfin.rs]
        |
        v
[Worker: resolve play URL → OpenRequest]
        |
        v
open_player(state, platform, request)         [src/main.rs]
        |
        +-- platform.webos == true
        |       |
        |       v
        |   state.launching = true
        |   state.web_player_item = item_id
        |   platform.send(Request::WebPlayer(params))
        |       |
        |       v
        |   [Luma Player web app plays video]
        |
        +-- platform.webos == false (desktop)
                |
                v
            [Local playback session]
                |
                v
[Remote: Back]
        |
        v
state.back()                                  [src/state.rs]
        |
        +-- playback_progress[id] = position_ms  [saved]
        +-- state.movie = None
        +-- focus → Target::MoviePlay
```

**Source owners:** `src/state.rs`, `src/main.rs`, `src/jellyfin.rs`, `src/plex.rs`, `src/media.rs`, `src/player.rs`

---

## Flow 3: Home stack refresh (Jellyfin example)

```
[Settings: linked Jellyfin server + stack configured]
        |
        v
stacks_refresh(state)                         [src/main.rs]
        |
        v
jellyfin_service().send(Command::Fetch(link, stacks))
        |
        v
[Worker: fetch() iterates collections]
        |
        +-- HTTP GET /UserItems/Resume etc.
        +-- card_id() FNV-1a hash → i64 (CARD_TAG bit)
        +-- poster download to cache dir
        |
        v
Response::Items(index, Vec<StackItem>)
        |
        v
main.rs jellyfin_tick()                       [src/main.rs]
        |
        v
state.stack_items[index] = items
        |
        v
[Renderer draws stack row via stacks_view.rs]
```

**Source owners:** `src/main.rs`, `src/jellyfin.rs`, `src/stacks.rs`, `src/stacks_view.rs`

---

## Flow 4: Nivío title launch (Phase 1, feature-gated)

```
[User action → Target::NuvioLaunch(target)]
        |
        v
state.activate()                              [src/state.rs]
        |
        +-- !self.launching guard
        +-- focus UNCHANGED (preserved for Back)
        |
        v
Effect::NuvioLaunch { content_target: target }
        |
        v
main.rs effects()                             [src/main.rs]
        |
        +-- platform.webos == true
        |       |
        |       v
        |   state.launching = true
        |   platform.send(Request::NuvioLaunch { content_target })
        |       |
        |       v
        |   [Platform worker: validate_nuvio_target()]
        |       |
        |       +-- invalid → Err("Invalid Nuvio content target")
        |       |       |
        |       |       v
        |       |   Response::Launched(Err) — NO TV call made
        |       |
        |       +-- valid → luna://com.webos.applicationManager/launch
        |       |           {"id": "space.nuvio.webos", "params": {"contentTarget": target}}
        |       |       |
        |       |   TV reply → Response::Launched(Ok/Err)
        |       |       |
        |       |   Err → app_not_installed() + getAppInfo preflight
        |       |       |
        |       |   NUVIO_NOT_INSTALLED → state.notify("Nuvio isn't installed.")
        |       |
        |       v
        |   state.launching = false
        |   state.dirty = true
        |
        +-- platform.webos == false (desktop)
                |
                v
            state.notify("Desktop preview · Nuvio will open on your TV.")
        |
        v
[Back out of Nivío → focus unchanged → returns to same position]
```

**Source owners:** `src/platform.rs`, `src/state.rs`, `src/main.rs`, `assets/messages.json`

---

## Flow 5: Preferences save

```
[User changes a setting]
        |
        v
Effect::Save
        |
        v
main.rs effects()                             [src/main.rs]
        |
        v
storage::save(preferences_path, &preferences) [src/storage.rs]
        |
        +-- Atomic temp-file rename
        +-- One instance per preferences file
        |
        v
[Preferences persisted to TV storage]
        |
        v
Err → state.notify(savedError)
```

**Source owners:** `src/storage.rs`, `src/main.rs`, `src/model.rs` (sanitize)

---

## Flow 6: Weather refresh

```
[Home visible + widget enabled + city configured]
        |
        v
weather_tick()                                [src/main.rs]
        |
        v
weather_service().send(FetchForecast)         [src/weather-service.rs]
        |
        v
[Worker: HTTP GET Open-Meteo, 8s timeout, 256KiB limit]
        |
        v
[Generation ID prevents stale responses]
        |
        v
[Cache: fresh for 15 min, valid up to 6 hours]
        |
        v
state.weather updated
        |
        v
[Renderer draws weather widget/headline]
```

**Source owners:** `src/weather-service.rs`, `src/weather.rs`, `src/main.rs`
