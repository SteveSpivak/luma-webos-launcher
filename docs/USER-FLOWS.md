# User Flows — Nuvio TV Integration

Text-based flow diagrams for every screen, interaction, transition, and UX behavior. All flows are grounded in the actual source code (`src/state.rs`, `src/main.rs`, `src/platform.rs`, `src/stacks_view.rs`, `src/view.rs`).

## Flow 1: Enter → Launch Nuvio title (Phase 1)

```
[User on Home or Apps screen]
        |
        v
[Focus on a future Nuvio stack card OR menu action]
        |
        v
[User presses OK / Enter]
        |
        v
state.activate()
        |
        +-- focus == Target::NuvioLaunch(target) && !state.launching
        |       |
        |       v
        |   Effect::NuvioLaunch { content_target: target }
        |       |
        |       v
        |   state.focus UNCHANGED (preserved for Back)
        |       |
        |       v
        |   main.rs effects() → platform.send(Request::NuvioLaunch { content_target })
        |       |
        |       v
        |   [Platform worker thread]
        |       |
        |       +-- validate_nuvio_target(target) == Err
        |       |       |
        |       |       v
        |       |   Response::Launched(Err("Invalid Nuvio content target"))
        |       |       |
        |       |       v
        |       |   state.launching = false
        |       |   state.notify("Invalid Nuvio content target")
        |       |
        |       +-- validate == Ok && platform.webos == true
        |               |
        |               v
        |           luna://com.webos.applicationManager/launch
        |           {"id": "space.nuvio.webos", "params": {"contentTarget": target}}
        |               |
        |               v
        |           TV reply Ok → Response::Launched(Ok)
        |           TV reply Err → classify error
        |               |
        |               +-- app_not_installed OR getAppInfo says absent
        |               |       |
        |               |       v
        |               |   Response::Launched(Err(NUVIO_NOT_INSTALLED))
        |               |   state.notify("Nuvio isn't installed.") [translated]
        |               |
        |               +-- other error
        |                       |
        |                       v
        |                   Response::Launched(Err(other))
        |                   state.notify("This app couldn't be opened.")
        |               |
        |               v
        |           state.launching = false
        |           state.dirty = true
        |           |
        |           v
        |   [Renderer redraws with notice]
        |
        +-- state.launching == true (duplicate in flight)
        |       |
        |       v
        |   activate() returns [] (empty)
        |   No platform.send() called
        |
        +-- platform.webos == false (desktop)
                |
                v
            state.notify("Desktop preview · Nuvio will open on your TV.")
            state.launching unchanged
```

### Screens involved
- Home (focus on stack card — Phase 2) or menu action (Phase 1 programmatic trigger)
- No new screen created; launch is silent with optional notice

### Interactions
- OK / Enter on Nuvio card → launch request
- No keyboard injection
- No autoplay decision by Luma

### Transitions
- `state.launching: false → true` (webOS) during round trip
- `state.dirty: false → true` triggers re-render
- Notice appears/disappears per `state.notify()` timing

### UX / UI
- No Nuvio UI rendered by Luma — Nuvio app owns its own detail page
- Luma shows only a transient notice (desktop preview or error)
- Focus remains where it was; Back returns to same focus

---

## Flow 2: Back out of Nuvio (Phase 1)

```
[User leaves Nuvio app via TV Back button]
        |
        v
[Luma regains foreground]
        |
        v
[User presses Back on remote]
        |
        v
state.back()
        |
        +-- state.movie is None && state.playback is None && state.album is None
        |       && state.overlay is None && state.ha_camera is None && state.game is None
        |       |
        |       v
        |   [Existing Back logic: settings pop, page back, or quit]
        |
        v
[Focus is still Target::NuvioLaunch(...) — unchanged by launch]
        |
        v
[User is back at the same position in Luma]
```

### Screens involved
- Nuvio app (full screen, owned by Nuvio)
- Luma Home/Apps (returns to previous focus)

### Interactions
- TV Back button → leaves Nuvio app
- Luma Back button → existing navigation (no Nuvio-specific handling)

### Transitions
- None in Luma state (launch did not modify focus or page)

### UX / UI
- Seamless return — user doesn't notice Luma state changed
- Focus ring reappears on the same card

---

## Flow 3: Invalid target rejection (negative test)

```
[Integration test or malformed input]
        |
        v
Request::NuvioLaunch { content_target: "nuvio://tmdb/movie/abc" }
        |
        v
Platform worker: validate_nuvio_target("nuvio://tmdb/movie/abc")
        |
        +-- kind == "movie" OK, but id "abc" fails is_ascii_digit
        |       |
        |       v
        |   Err("Invalid Nuvio content target")
        |
        v
Response::Launched(Err("Invalid Nuvio content target"))
        |
        v
state.launching = false
state.notify(...) [error surfaced]
        |
        v
[NO TV service call was made]
```

### Screens involved
- None (test or error path only)

### Interactions
- No user interaction; programmatic rejection

### Transitions
- `state.launching` never set to `true` (rejection happens before launch flag)

### UX / UI
- Error notice if surfaced through UI path
- Silent rejection in test path

---

## Flow 4: Missing Nuvio app (negative test)

```
[Platform worker, webOS]
        |
        v
Request::NuvioLaunch { content_target: "nuvio://tmdb/movie/603" }
        |
        v
validate_nuvio_target() == Ok
        |
        v
luna://com.webos.applicationManager/launch {"id": "space.nuvio.webos", ...}
        |
        v
TV replies: returnValue=false, errorText contains "not installed"
        |
        v
app_not_installed(error) == true
        |
        v
Response::Launched(Err(NUVIO_NOT_INSTALLED))
        |
        v
main.rs: error == platform::NUVIO_NOT_INSTALLED
        |
        v
state.notify("Nuvio isn't installed.") [translated per language]
state.launching = false
state.dirty = true
        |
        v
[Renderer shows notice; focus unchanged]
```

### Screens involved
- Luma Home (notice overlay)
- No Nuvio screen (app not installed)

### Interactions
- User pressed OK on Nuvio card (or programmatic trigger)
- Notice appears; user dismisses or it times out

### Transitions
- `state.launching: false → true → false`
- Notice state: None → Some → None

### UX / UI
- Clear translated notice
- No confusion about what happened

---

## Flow 5: Desktop preview (no TV)

```
[Developer on desktop, no webOS feature]
        |
        v
Request::NuvioLaunch { content_target: "nuvio://tmdb/movie/603" }
        |
        v
main.rs effects(): platform.webos == false
        |
        v
state.notify("Desktop preview · Nuvio will open on your TV.")
        |
        v
[No Luna service call; no TV interaction]
        |
        v
[Notice shown; launch is a no-op on desktop]
```

### Screens involved
- Desktop preview window

### Interactions
- User triggers launch on desktop

### Transitions
- None in platform (no `state.launching = true` on desktop)

### UX / UI
- Informative notice
- No false impression that launch succeeded

---

## Flow 6: Future Phase 2 — Continue Watching stack row (BLOCKED)

```
[Nuvio producer publishes Continue Watching — NOT IN THIS REPO]
        |
        v
[Future: nuvio::Service worker fetches Continue Watching items]
        |
        v
Response::Items(index, Vec<StackItem>) → state.stack_items[index]
        |
        v
stacks_view.rs home_stacks() renders "Continue Watching" row
        |
        v
[User focuses Nuvio stack card (Target::StackCard(row, index))]
        |
        v
[User presses OK]
        |
        v
state.activate() → open flow for stack card
        |
        +-- Future: card has contentTarget → Effect::NuvioLaunch
        |       |
        |       v
        |   [Same as Flow 1]
        |
        +-- Future: card has media id → open_movie() → Effect::MediaDetails
                |
                v
            [Jellyfin/Plex-style playback — NOT for Nuvio]
```

### Screens involved
- Home screen with Nuvio Continue Watching row (future)
- Nuvio detail page (owned by Nuvio app)

### Interactions
- D-pad navigation within row and between rows
- OK on card → launch
- Back → return to same focus

### Transitions
- `state.stack_scroll` per row (existing stack scroll logic)
- Focus tween animation (existing motion system)

### UX / UI
- Reuses existing poster card rendering
- No new UI framework
- Source label shows "Nuvio" (future: add to `source_label()` in `stacks_view.rs`)

**BLOCKED:** No Nuvio producer API exists. This flow cannot be implemented until a Nuvio owner authorizes a publish contract.

---

## Screen inventory (existing, reused)

| Screen | Owner file | Nuvio Phase 1 changes | Nuvio Phase 2+ changes |
|---|---|---|---|
| Home | `src/state.rs`, `src/view.rs`, `src/stacks_view.rs` | None | Add Nuvio row (future) |
| Apps | `src/state.rs`, `src/view.rs` | None | None |
| Settings › Stacks | `src/state.rs` | None | Add "nuvio" source (future) |
| Movie/title card | `src/state.rs`, `src/movie.rs` | None | None (Nuvio titles open in Nuvio app) |
| Settings › Stacks config | `src/state.rs` | None | Add Nuvio collections (future) |
| Notice/toast | `src/state.rs` `notify()` | `nuvioNotInstalled` message | Same |

## Interaction inventory

| Interaction | Trigger | Handler | Phase 1 change |
|---|---|---|---|
| Launch Nuvio title | Programmatic / future card OK | `state.activate()` → `Effect::NuvioLaunch` | Added `Target::NuvioLaunch` arm |
| Duplicate launch | Rapid OK while launching | `!self.launching` guard | Same guard extended to NuvioLaunch |
| Back after Nuvio | TV Back / Luma Back | `state.back()` | None (focus preserved) |
| Invalid target | Malformed input | `validate_nuvio_target()` | New function |
| Missing app | TV error reply | `app_not_installed()` + `getAppInfo` | New error constant + handling |
| Desktop preview | Desktop build | `desktopPreview` notice | Added Nuvio case |

## Transition inventory

| Transition | From | To | Trigger | Phase 1 change |
|---|---|---|---|---|
| Launch start | idle | launching | `platform.send(Request::NuvioLaunch)` | `state.launching = true` (webOS) |
| Launch success | launching | idle | `Response::Launched(Ok)` | `state.launching = false`, `dirty = true` |
| Launch error | launching | idle | `Response::Launched(Err)` | `state.launching = false`, notice |
| Invalid target | — | — | `validate_nuvio_target() == Err` | No launch flag set |
| Desktop | — | — | `platform.webos == false` | Notice only, no flag |

## Back precedence (existing, preserved)

`state.back()` order of precedence:
1. Ambient mode → leave ambient
2. Moving selection → cancel move
3. Game shot → clear shot
4. Game active → close game
5. Album active → close album
6. Playback active → close playback (saves progress)
7. Movie active → close movie (saves progress)
8. Overlay → dismiss overlay
9. Settings subpage → close subpage
10. Settings section → pop section
11. Page → previous page
12. Home → quit application

**Nuvio Phase 1 does not insert into this chain** — focus is preserved, so Back behaves exactly as before.