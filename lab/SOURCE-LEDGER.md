# Sources, ownership and transfer ledger (2026-11-05)

Target **PUBLIC** repo `SteveSpivak/luma-webos-launcher`, advanced baseline `40994fc144b5af481056d14e2fb93304aa1e2c82`. User's older Luma and some other repos may be private; do not escalate data visibility merely to make Arena convenient.

| Source | SHA | What it owns | Transferred | What is NOT copied |
|---|---|---|---|---|
| `funnymataleao/luma-webos-launcher` (forked as target) | `40994fc144b5af481056d14e2fb93304aa1e2c82` | Runtime, Rust GUI, motion, media, widgets, app manager and build | **Already in this repo**, exact fork HEAD | No need to duplicate upstream files |
| `SteveSpivak/lg-luma` | `1bef79683968841426d89f066bd5bf1c0e3bbe31` | Older fork, damage, EGL instrumentation, old focus experiment, forensic evidence | Selected **13** source-backed reference tools/docs/tests under `lab/`; see manifest | Don't apply patch or import old `src/`/Home hooks |
| `SteveSpivak/nuvio-perf-lab` | `c97c38da61511fc5b644680aabb6e646f9785f1d` | Nuvio app, deep links, watch history, profiles, player, Nuvio measurements | Non-secret *derived interoperable* contract and tests only | PRIVATE full JS code, auth, account, addons, player |
| `SteveSpivak/LG-TV` | `333f1b9b5d8fc36965491d9590a2273481a596a3` | Device ops, recovery, LG network/privacy/hooks | High-level protected-feature and rollback policy | PRIVATE root scripts, private configs, device/network details |
| `SteveSpivak/nuvio-perf-lab` upstream `lab` | `dba4a806703c11be71fdfc9d28b2c369915a90c1` | Long-running lab owner | Reference only, not auto-sync | Research branches unrelated to integration |

## Required dependencies and exact upstream paths to inspect
- Advanced: `src/platform.rs` (one worker for `Launch`), `src/state.rs` (navigation), `src/view.rs`, `src/motion.rs`, `src/widgets.rs`, `src/smart_home.rs`, `src/hw_wallpaper.rs`, `native/smp/`, `appinfo.json`, `Cargo.lock`, `pnpm-lock.yaml`, `flake.lock`, `development.md`.
- Private Nuvio (read authorized source in its repo; no copying to public): `appinfo.json`, `js/core/deeplink/deepLinkParser.js`, `js/core/deeplink/launchDeepLink.js`, `js/ui/navigation/router.js`, `js/ui/screens/stream/streamScreenMethods-08-build-web-os-native-player-launch-parameters.js`, `lab/checks/launch-intent.test.mjs`, `lab/research/launcher-coldstart-2026-11-02/FEATURE-ROUTING.md`.
- Old Luma (copied reference): `lab/references/lg-luma/research/luma-audit/*` and `lab/legacy-luma/scripts/*`. `lab/reference-import-manifest.json` supplies exact source blob hashes.
- LG-TV: check independent recovery and installed app identity in its own repo; do NOT bring owner-only SSH materials to target.

## Implementation rule
Copy code only if a documented target owner does not already exist. Use adapter behind default OFF, no fork-wide refactors. Retain upstream changes/credits and source provenance. Any later private-code transfer to this public repo requires separate explicit review of licensing, sensitive content and publication intent; no silent transfer.
