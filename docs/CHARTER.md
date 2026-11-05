# Project Charter — Nuvio TV Integration (Luma Launcher)

## 1. Purpose

Integrate the Nuvio TV application (`space.nuvio.webos`) into the Luma native launcher so a Luma user can open a Nuvio title directly into its detail page, with Nuvio remaining the sole owner of playback, accounts, profiles, and library state.

This charter covers **Phase 1: title-to-detail launch** only. Phase 2 (Continue Watching stack row) and Phase 3 (first-class Home row) are scoped separately and depend on a Nuvio producer API contract that does not yet exist in this repository.

## 2. Goals (in scope)

- Luma owns the app-launch request; Nuvio owns the deep-link receiver, playback, accounts, and profiles.
- Default-off `nuvio` feature flag so default builds are unchanged.
- Fixed, validated Nuvio application ID: `space.nuvio.webos`.
- Validated movie and series content targets only: `nuvio://tmdb/movie/<digits>` and `nuvio://tmdb/tv/<digits>`.
- Explicit error handling when Nuvio is absent from the TV.
- Safe launch parameter construction: `{"id": NUVIO_APP_ID, "params": {"contentTarget": ...}}`.
- No autoplay, no new media player, no synthetic keyboard-event injection.
- Duplicate launch requests blocked while one is in flight.
- Focus preserved so Back out of Nuvio returns to Luma with the same focus.
- No account, profile, token, or streaming-URL parameters sent by Luma.

## 3. Non-goals (explicitly out of scope)

- No Nuvio playback engine inside Luma.
- No Nuvio account database or profile storage inside Luma.
- No unauthenticated LAN endpoint for Nuvio data.
- No Continue Watching feed consumed unless a real Nuvio producer contract is authorized.
- No independent Nuvio UI framework or rendering system.
- No physical TV operations, firmware changes, root services, or device installation.
- No modification of LG Home, HDMI/CEC, HomeKit/AirPlay, DRM, or System Settings.

## 4. Constraints

- All work on branch `arena/5fe14abb-luma-webos-launcher`; `main` unchanged.
- Submit via draft PR only; do not merge automatically.
- Keep existing advanced Luma capabilities (motion, widgets, Jellyfin/Plex/Moonlight stacks, video wallpaper) intact.
- Experimental functionality default OFF.
- No new general-purpose API server.
- No native build or test execution possible in this sandbox (no Rust toolchain, no pnpm). Native validation receipts are BLOCKED until a toolchain is available.

## 5. Roles and ownership

| Concern | Owner | Source files |
|---|---|---|
| Application launch to TV services | Platform | `src/platform.rs` |
| Home state, navigation, effects, focus | State | `src/state.rs` |
| Effect dispatch, response handling | Main | `src/main.rs` |
| Stack source registry, card items | Stacks | `src/stacks.rs` |
| Stack card rendering | Stacks view | `src/stacks_view.rs` |
| App tiles and focus rendering | View | `src/view.rs` |
| Shared media types, poster cache | Media | `src/media.rs` |
| Installed app artwork | App artwork | `src/app_artwork.rs` |
| Translations | i18n | `src/i18n.rs`, `assets/messages.json` |
| Tests | Tests | `src/tests.rs` |

## 6. Success criteria (Gate 1)

- Source-complete Phase 1 implementation committed on the branch.
- Draft PR #2 open against `main`.
- All 11 Phase 1 requirements addressed in source.
- 8 feature-gated unit tests present in `src/tests.rs`.
- Native build and test run: **BLOCKED** — no Rust toolchain in this sandbox. Cannot claim PASS.
- Rollback instructions documented.

## 7. What this charter is NOT

- Not a design for an independent Nuvio subsystem.
- Not a runtime measurement report (cannot be produced without a toolchain).
- Not authorization to operate on any physical TV.