# User Stories — Nuvio TV Integration (Phase 1)

All stories are grounded in the actual source architecture. Acceptance criteria are expressed in terms of state/effect transitions that can be tested via `src/tests.rs`.

## Story 1: Launch a Nuvio movie into its detail page

**As a** Luma user on the Home screen,
**I want to** open a Nuvio movie by its content target,
**So that** Nuvio shows me the title's detail page and I can choose to play it.

### Acceptance criteria
1. Given a valid target `nuvio://tmdb/movie/603`, when the user triggers launch, then `Effect::NuvioLaunch { content_target: "nuvio://tmdb/movie/603" }` is produced.
2. Given `platform.webos == true`, the platform worker sends `luna://com.webos.applicationManager/launch` with `{"id": "space.nuvio.webos", "params": {"contentTarget": "nuvio://tmdb/movie/603"}}`.
3. Given `platform.webos == false` (desktop), a `desktopPreview` notice is shown instead of calling TV services.
4. Focus is NOT moved by the launch — `state.focus` remains `Target::NuvioLaunch(...)` after `activate()`.
5. `state.launching` is set to `true` on webOS during the launch round trip.
6. No account, profile, token, or streaming-URL parameters are included in the launch payload.

### Test coverage
- `nuvio_launch_params_match_the_contract` — verifies payload shape
- `nuvio_launch_keeps_focus_for_back_restoration` — verifies focus preservation
- `nuvio_target_validates_movie_and_series_identifiers` — verifies valid targets

---

## Story 2: Launch a Nuvio series into its detail page

**As a** Luma user,
**I want to** open a Nuvio TV series by content target,
**So that** I can browse its episodes in Nuvio.

### Acceptance criteria
1. Given a valid target `nuvio://tmdb/tv/129973`, `validate_nuvio_target()` returns `Ok(...)`.
2. The launch proceeds identically to the movie case (same app ID, same parameter shape).

### Test coverage
- `nuvio_target_validates_movie_and_series_identifiers` — covers `nuvio://tmdb/tv/129973` and `nuvio://tmdb/tv/1`

---

## Story 3: Malformed content target is rejected

**As a** Luma user (or integration),
**I want** invalid Nuvio targets to be rejected before any TV service is called,
**So that** no invalid deep-link is ever sent to the TV.

### Acceptance criteria
1. Empty string → `Err("Invalid Nuvio content target")`
2. `nuvio://tmdb/movie/` (no ID) → error
3. `nuvio://tmdb/movie/abc` (non-numeric) → error
4. `nuvio://tmdb/movie/603/` (trailing slash) → error
5. `nuvio://tmdb/episode/603` (wrong kind) → error
6. `nuvio://tmdb/movie/603?autoplay=1` (query string) → error
7. `nuvio://other/movie/603` (wrong host path) → error
8. `NUVIO://TMDB/MOVIE/603` (uppercase) → error
9. `nuvio://tmdb/movie/603 ` (trailing space) → error
10. `tmdb/movie/603` (missing scheme) → error
11. `https://nuvio.example/movie/603` (wrong scheme) → error
12. No TV service call is made for any invalid target.

### Test coverage
- `nuvio_target_rejects_malformed_targets` — all 11 cases

---

## Story 4: Nuvio app not installed

**As a** Luma user,
**I want** a clear notice when Nuvio is not installed on the TV,
**So that** I understand why the title didn't open.

### Acceptance criteria
1. When the TV replies that Nuvio is not installed (launch error classified by `app_not_installed()` or confirmed by `getAppInfo`), `state.notify("Nuvio isn't installed.")` is shown (English).
2. The notice is translated in de/es/zh/pt.
3. `state.launching` is set to `false` after the error.
4. Other launch errors (network, timeout) still show the generic `appOpenError` notice.

### Test coverage
- Not directly unit-testable without a TV; covered by source inspection of `Response::Launched` error handling in `src/main.rs`.
- `nuvio_invalid_target_is_rejected_before_reaching_tv_services` — verifies invalid targets fail before any TV call.

---

## Story 5: Duplicate launch blocked

**As a** Luma user,
**I want** a second launch request to be ignored while one is already in flight,
**So that** no duplicate `contentTarget` requests are sent to the TV.

### Acceptance criteria
1. When `state.launching == true`, `activate()` on `Target::NuvioLaunch` returns an empty effect vector.
2. No `platform.send()` is called for the duplicate request.
3. Once the first launch completes (`state.launching = false`), a new launch is allowed.

### Test coverage
- `nuvio_duplicate_launch_is_blocked_while_launching` — sets `launching = true`, verifies `activate()` returns empty.

---

## Story 6: Back out of Nuvio returns to Luma with same focus

**As a** Luma user,
**I want** pressing Back after leaving Nuvio to return me to Luma with the same focus I had before launching,
**So that** my place in the interface is preserved.

### Acceptance criteria
1. `activate()` on `Target::NuvioLaunch` does not change `state.focus`.
2. After the launch completes (success or error), `state.focus` is still `Target::NuvioLaunch(...)`.
3. Existing `state.back()` behavior applies — no Nuvio-specific Back handling needed.

### Test coverage
- `nuvio_launch_keeps_focus_for_back_restoration` — verifies `state.focus` unchanged after `activate()`.

---

## Story 7: Default-off feature

**As a** Luma user or administrator,
**I want** the Nuvio integration to be disabled by default,
**So that** existing installations are unaffected unless the feature is explicitly enabled.

### Acceptance criteria
1. `nuvio` is NOT in `default = []` in `Cargo.toml`.
2. Default builds (`cargo build` without `--features nuvio`) compile without Nuvio code.
3. All Nuvio-specific code is behind `#[cfg(feature = "nuvio")]`.
4. No dead_code warnings for Nuvio constants in default builds.

### Test coverage
- Cannot be unit-tested; verified by source inspection and CI `cargo clippy -D warnings` (BLOCKED: no toolchain).

---

## Story 8: Platform worker routing (desktop test)

**As a** developer,
**I want** the Nuvio launch to route through the real `Platform` worker on desktop,
**So that** the code path is exercised without a TV.

### Acceptance criteria
1. `Platform::new(true)` with a `Request::NuvioLaunch` produces `Response::Launched(Err(...))` on desktop (Luna services unavailable).
2. The error message indicates Luna services are only available on ARM webOS builds.
3. Invalid targets are rejected before reaching the `call()` stub.

### Test coverage
- `nuvio_launch_routes_through_the_platform_worker` — `Platform::new(true)`, verifies error message.
- `nuvio_invalid_target_is_rejected_before_reaching_tv_services` — verifies pre-validation rejection.

---

## Stories NOT in scope (Phase 2+, blocked)

- Continue Watching row on Home
- Watchlist row on Home
- Nuvio account sign-in from Luma
- Nuvio profile switching from Luma
- Nuvio playback progress sync to Luma
- Nuvio artwork feed consumption