# Cross-repo forensic lessons relevant to the advanced Luma fork

## Existing evidence, do not rediscover
- Advanced `funnymataleao/luma-webos-launcher` at `40994fc1` (MIT) is a **sibling** of `SteveSpivak/lg-luma` base `e5608cd0`. Forensic audit at `1bef7968`: 179 common paths, 126 byte-identical blobs, 53 changed, 41 Rust modules unique to the advanced version, 22 to old fork. Static comparison, not build/TV performance.
- Old Luma experiment `LUMA_FOCUS_DEPTH=1` is an **unapplied patch against the old fork** and NOT PORTABLE here. Advanced fork already has `motion.rs` continuous tween / spring / zoom / halo and 123 reduced-motion gates counted in prior audit. Shadow fill area and calculated bandwidth do not equal GPU runtime.
- Advanced widgets/HA/Jellyfin/Plex/Moonlight and `native/smp`/video wallpaper are present source modules. Their existence does not guarantee compatibility with owner's webOS or grants permission to use vendor media plane APIs. Don't build duplicate renderers, decoder, navigation owners, or camera streams.
- Prior native test limitations: Rust/Cargo, SDL2, pnpm, Xvfb missing in Arena. Previous agent's `63 pass` is historical on old Luma research tooling; new fork must rerun and label actual execution environment. Receipts from reset workspace may be `committed_historical`, never 'rerun'.
- Prior old Luma cold wallpaper decode/upload can occur on SDL thread; GPU vector geometry caches have missing aggregate eviction. These are defects to **check for in the advanced fork**, not assume they're identical.
- Earlier Luma comparison flagged resting Apps card shadows skipping focus cost. Treat as design trade-off, not automatic optimization, and test screenshot/focus semantics.
- Nuvio has a documented one-title launch contract and a separate lab-only synthetic keyboard intent. Never confuse them. Continue Watching needs an **export producer contract** and profile-aware privacy; no evidence the existing deep-link parser publishes a feed.
- Nuvio v1.3.6 migration research includes many branches and incomplete testing; source code under `c97c38da` is pinned historical, not automatically newest or installed on owner's TV.
- TV essential functions: native AirPlay/HomeKit, Magic Remote/D-pad/Back, voice, HDMI/CEC, audio, LG Store/updates, DRM, Settings and independent recovery. Do not infer a service is disposable from its name.
- For media, `loading`, `ready`, `playing`, `currentTime>0`, and *visually observed first frame* are different states. One media owner, bounded decode, generation/cancellation and cleanup; no animation/transforms of protected video layers.
- Test integrity: negative controls for stale git HEAD, unexpected changed files, corrupt JSON, missing source/SDK, metrics empty input; unrun real-TV = NOT_RUN, not PASS. Two repeated failures -> stop.
- Secrets: no tokens, app credentials, account/profile IDs, device MACs, full URLs of addons, HARs or proprietary vendor binaries in repository; redacted receipts only.
