# Separate approval-gated device validation plan

**Current verdict: NOT-READY. Physical-TV actions: NOT_RUN. No TV was contacted.** The synthetic fixture `../fixtures/device-preflight-not-ready.json` intentionally leaves identity, firmware, recovery and protected functions UNKNOWN. It is not a scan result.

## Approval and preflight gate

Before any device command, obtain explicit owner approval naming the device, scope and permitted read-only or canary operations. Then establish:

1. Exact model/firmware and source/candidate/package hashes; no inference from a hostname or firmware string alone.
2. Independent recovery route not dependent on the experimental Home or LAN; known-good package cached and verified; Home-owner conflict checked.
3. Home, Home button, Magic Remote D-pad/Back and LAN control healthy. AirPlay/HomeKit, audio/voice, HDMI/CEC, Settings/updates and representative streaming launch must be preserved.
4. A physical fallback input and owner present. Unknown recovery/protected function is a blocker, not a warning to bypass.
5. No firmware, DNS, media-protection, system-service or TV-configuration mutation. No rooting/install/Home-hook scripts imported from reference snapshots.

The bundled LG preflight/dependency contracts guide this gate but cannot prove readiness. Full JSON-Schema validation and live preflight have not run.

## Stage A — approved read-only census

Capture only allowlisted observations: actual process maps/library paths, ELF `DT_NEEDED`/symbol versions and SHA-256, EGL client extensions/current context, SDL backend, drawable/sample count/display mode, compositor/plane state where readable, process memory and relevant public media headers/permissions. Do not dump environment, credentials, network keys, account data or protected media. Hash raw files before redaction; keep raw output outside checkout.

Falsify assumptions if the loaded SDL/EGL/LS2 libraries differ from the build/runtime pins, the context is not EGL, partial-update extensions are absent, or media APIs lack a documented permitted route. A library name/symbol is not proof of a working call path.

## Stage B — desktop/native gate before TV canary

Restore the documented Rust/SDL/pnpm toolchain and installed dependencies; do not substitute host timing for TV timing. Run baseline and candidate:

- `cargo test --locked --workspace --all-features`
- `pnpm test`, `pnpm check`, `pnpm format:check`
- dependency-free and mocked desktop smoke suites as documented
- candidate focus tests, existing damage/recents/input/settings/storage regressions
- default-off scene equality and enabled-only shadow difference
- partial/full damage verification at actual desktop drawable; no TV claim

Only a separately approved, bounded candidate package may proceed. The current unapplied patch is not that package.

## Stage C — approved UI canary

Use isolated preferences and exact environment opt-in; no new persistent setting. Compare baseline and candidate with identical assets, refresh, thermal state and scripts. Keep true idle separate from forced-redraw profiling. Initial four A/B/B/A cycles (eight adjacent pairs), extend from observed variability and predefined worthwhile effect. Record treatment identity in every run.

Metrics: p95/p99 presentation-call intervals, input-to-first-visible-call, idle wakeups/presents, cache counters, RSS/PSS slope if available, damage coverage/mismatch, focus/Back correctness and cleanup. GPU time/memory remain UNKNOWN without calibrated measurement. Verify reduced motion, pointer stability, stale inventory/input/Recents replies, hidden/focus-loss behavior and modal restoration.

Then manually check Home identity/button, remote navigation, input switching, audio, AirPlay/HomeKit, Settings/update availability and protected streaming launch. Stop on any regression; do not infer these from a successful UI screenshot.

## Stage D — separate real-video approval

Even an approved UI canary does not authorize video. Follow `video-feasibility.md`: first supported-player handoff with owner-owned unprotected media; only then consider a separately approved media-plane/import probe. No DRM interception or system compositor reconfiguration. Stop if plane/audio/focus ownership or cleanup is uncertain.

## Evidence and clock alignment

Keep native diagnostics as the source; adapt offline into the lens evidence discipline, not a second collector/service. Preserve `source_environment`, metric IDs/units, evidence class, null unavailable values and redaction. The current lens schema fixes `agent.name` to webos-lens and its correlation output says browser; a native adapter must identify the actual exporter/receipt type rather than falsely label Luma as a browser or lens agent.

For cross-domain timing require a documented shared marker, explicit clock domains, finite nonnegative maximum error, supporting evidence and `same_specimen: true`. Close timestamps are insufficient. Never merge process-memory measurements with texture/compositor arithmetic. Our synthetic correlation tests validate refusal rules only; no alignment was measured.

## Rollback boundary

For the current delivery, native files are unchanged and there is nothing to roll back on a TV. For a future approved canary, unset the experiment environment, stop only its process, restore isolated preferences if used, and verify the predeclared known-good package/Home route. Do not run reference recovery scripts automatically. See `../../delivery/rollback.md`.
