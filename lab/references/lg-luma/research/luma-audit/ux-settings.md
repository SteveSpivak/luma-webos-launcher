# Native UX and settings review

## Existing behavior to preserve

| Surface | Source-backed behavior | Decision |
|---|---|---|
| Home cards | One horizontal favorites strip; 256×154.4 face, 281.6 pitch; edge clipping/fades; whole-card remote reveal (`state.rs:20–27, 760–807`, `view.rs:1208–1256`) | Keep geometry and navigation. Do not import a content-catalog hero into an app launcher. |
| Focus | Existing ring, larger/deeper shadow, heavier caption and press dimming (`view.rs:781–891`) | A bounded depth-only experiment is lower risk than changing card scale/hit regions. |
| Apps grid | Six-column index navigation including offscreen rows; fixed toolbar priority (`state.rs:1390–1435`, tests `apps_toolbar_stays_fixed_above_scrolling_cards_and_keeps_pointer_priority`) | Preserve; no nearest-neighbor replacement. |
| Pointer | Hover/down cannot reveal-scroll a clicked control; release must hit the original target (`main.rs:1450–1506`, `state.rs:808–829`) | Any visual transform must not invalidate this contract. |
| Back / Recents | 600 ms hold; overlay dismissal consumes the press; depth-sorted Recents cards; generation-tagged replies; no synthetic kill-all | Reuse existing state machine. Nuvio router history is not a replacement. |
| Reduced motion | Preference disables panel, wallpaper and notification animation; Recents settles immediately (`state.rs:373–437`, `recents.rs:195–245`) | New motion must honor it. The supplied depth candidate introduces no timer or motion. |
| Settings | Interface / Background / Widgets / System; nested breadcrumb path and explicit parent restoration (`view.rs:2094–2216`, `state.rs:985–1030`) | Already grouped. Do not add a second accordion/state owner merely to resemble Nuvio. |

## Verified Nuvio reference patterns, translated not copied

Official upstream pin `657c8a308d0c36aca1625a5e9293b3ba651f017b` was accessible; selected blobs were checked against its Git tree. This is **not** verification of the inaccessible V5 lab pin.

- `homeFocusPolicy.js:5–49`: late focus requires identity matching and must not override user interaction. Luma already reconciles missing app/input identities and defers input snapshots during presses. Preserve identity-based restoration rather than copying DOM dataset logic.
- `homeScreenMethods-15-schedule-focused-poster-flow.js:46–124`: focus flow uses a key/token, delay and current-focus checks before activation. If Luma ever adds delayed previews, use a monotonic deadline plus generation/focus checks in the existing loop; cancel on Back, focus loss and inventory replacement. No such preview is implemented here.
- `homeScreenMethods-13-mount-trailer-layer.js`: mounting/loading is not playback; cleanup and fallback are explicit. Translate to a future media owner only after API feasibility, not to `Draw::Image`.
- `ambientPlaybackPolicy.js:1–13`: require actual playing state, not a mounted element. Native equivalent must require decoder/frame progress plus visible/focused ownership.
- `routerMethods-03-back.js:8–75`: local Back consumption precedes route history. Luma's overlay/move/subpage precedence already implements the appropriate native contract; do not adopt browser history or exit behavior.
- `scripts/test-home-focus-scroll-policy.mjs`: constrained/legacy paths cancel animation and clamp scroll deterministically. Adapt the negative-test discipline to Rust, not requestAnimationFrame or DOM scrolling.

Nuvio is GPL-3.0; only behavioral observations are used. No upstream code/assets are copied into the candidate. The V5 Shared Hero implementation and its geometry remain UNKNOWN because that repository is blocked and the full V5 bundle is absent.

## Settings/companion capability matrix

| Area | Existing owner | Present safeguards / test evidence (native tests NOT_RUN) |
|---|---|---|
| Names, greeting, date/clock | `Preferences`, explicit widget subpages | Separate Home/Apps names; focus is not saved selection; keyboard completion routes and parent restoration tests exist. |
| Language / text rendering | `i18n.rs`, `text_rendering.rs` | Local translations; invalid enum recovery; MSAA chosen at window creation. Text-rendering changes require restart semantics, not a live GL-context swap. |
| Backgrounds | `wallpapers.rs`, `wallpaper_cycle.rs` | Bundled/uploaded catalog, fixed upload/cycle/gradient controls, selection/deletion focus restoration, independent manual splash, rotation state. |
| Inputs | `input_refresh.rs`, input settings | Cable state distinct from signal; On/Off/Auto; custom names retain port/status detail; slow snapshots cannot move a pressed card. |
| Weather | `weather*.rs` | Configured/enabled/visible Home only; latest-job generations; bounded HTTP; Celsius cache with display conversion; location removal clears cache. |
| Shortcuts | `tile_editor.rs`, `webhook.rs` | Bounded URLs/actions; QR editor; test/remove/list; commit acknowledgement/revision; no platform-app launch/uninstall through a webhook tile. |
| Updates/recovery | `update.rs`, `tv/self-update.sh`, helper | Feed/package allowlist, size and SHA-256 checks; installer verifies again. Existing shell tests use temporary fixtures/mocks, not a TV. Checksums are not an independent publisher signature. |
| Storage | `storage.rs` | Missing fields default; corruption fails closed; private app-owned destination selection; atomic replacement and failed-write cleanup tests exist. Directory fsync/power-loss behavior was not established. |

Companion sessions: 600 s lifetime; 20 s request deadline; wallpaper body ≤12 MiB and ≤64 requests/session; tiles body ≤4 KiB and ≤256 requests/session. One private/link-local IPv4 interface is selected, not `0.0.0.0`. Token, Host/Origin/Sec-Fetch-Site and action-header checks exist. HTTP is not TLS: possession of the LAN URL/token is the capability. Closing/focus loss revokes generations; committed edits can still apply after dialog dismissal because the client was already told they saved. Do not weaken these boundaries.

The dependency-free Node companion-page tests passed on this host. Rust session-expiry/corruption/cancellation tests remain BLOCKED. No server was opened on the real LAN by this audit.

## Candidate selection

1. **Chosen: default-off focus-depth shadow only.** Same face, caption, ring and hit rectangles; no new cache, animation clock or persistent setting. It is a candidate patch, not applied native implementation.
2. **Rejected for this gate: focus scaling/shared hero.** Changing geometry affects reveal, caption height, modal anchors, overlap and pointer stability; a shared hero adds content semantics Luma does not own.
3. **Rejected: Nuvio settings accordion import.** Existing native grouping and parent restoration already cover the useful pattern with less state.
4. **Deferred: trailer/animated card media.** No proven decoder/overlay contract; see `video-feasibility.md`.

Acceptance contracts for the candidate: exact `LUMA_FOCUS_DEPTH=1` opt-in; unset/invalid values preserve baseline draw parameters; reduced motion has no new motion to suppress; controls/artwork remain identical; old/new shadow bounds are included in damage; Back, stale replies and focus loss retain existing behavior; no aggregate cache growth. Native assertions are supplied in the patch but have not run.
