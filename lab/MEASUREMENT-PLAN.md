# Native Luma + Nuvio measurement and falsification plan

## Environments (must label each)
- **OFFLINE**: Python unit tests, schema, static inspection. No TV claim.
- **DESKTOP**: native SDL/GL simulator, same assets/profile/options under A/B/A. Not a webOS compositor.
- **TV**: physical LG model/firmware, exact app IPKs + hashes, display, remote, other apps. **NOT_RUN, owner approval required**.
- **CLOUD ARENA**: can run offline tests, not a substitute for macOS SDK or TV.

## Baseline
Pin commit `40994fc1`, toolchain (advanced fork `flake.lock` / `Cargo.lock` / `pnpm-lock.yaml`), `nix develop` reference. Read `development.md`; do not execute installers by default. Run available baseline `pnpm test`, `pnpm check`, Rust `cargo test --locked` and existing screenshot smoke **only where prereqs already installed**, with resource/time bounds. Record command, exit code, output SHA, test IDs, graphics backend, wallpaper/media state and profile config. No silent toolchain auto-install.

## A/B/A experiment
A = upstream advanced launcher, B = minimal default-OFF Nuvio feature enabled, A = disabled again. Same assets, render resolution, app inventory, wallpaper mode, input script, reset state and environment. Do NOT compare to old Luma as if it shares binary/draw loop. Collect 3+ bounded repetitions per condition (proposed; true repetitions selected before physical run). Do not use a compositor screenshot alone as proof of 4K panel output.

| Metric | Capture | Criterion | Counterexample |
|---|---|---|---|
| Cold/warm launch | monotonic process start -> first launcher UI ready; separate first *visible* frame when possible | distribution p50/p95, not a single best run | OS cache, login, source activity changes |
| D-pad response | input dequeued -> first swap call with corresponding changed focus | p50/p95/p99, no lost key / incorrect Back | swap call is not photons; no trace means UNKNOWN |
| Frame pacing | per-frame interval, samples, swap/CPU submission separately, idle wakeups separate | no material relative regression vs A, owner-defined budget | GPU submission ≠ actual GPU completion |
| UI visual stability | screenshot diff + damage-rect correctness / pointer-hit bounds | no unintended focus, zoom clipping or stale redraw | static screenshot hides animation defects |
| Memory/cache | actual RSS/PSS if available; renderer cache bytes (not total GPU) | stable slope in repeated navigation, no unbounded work queue | modeled frame bytes are not GPU memory |
| Nuvio title handoff | request accepted -> Nuvio detail ready, manual visual confirmation | correct movie/series, app id, navigation and Back | accepted launch ≠ correct detail, ≠ first frame |
| CW feed (later) | producer revision -> first displayed poster (cache hit/miss), profile | correct identity/progress, no cross-profile leak | cached feed from prior account shown |
| Offline mode | network unavailable only in isolated simulation first | static fallback, no frame stall and no root/network mutation | indefinitely pending background worker |
| Video wallpaper | native media owner disabled in Phase 1 | remain unchanged from A; later separate measured gate | leaking hardware plane during focus loss |

Quantiles must state sample counts, nearest-rank method and warmup exclusions. GPU estimates from shadow geometry remain MODEL. No arbitrary hardware speedup or MB budget claims. Use copied `lab/legacy-luma/scripts/native_metrics.py` and `analyze_native_diagnostics.py` *only if compatible with actual log schema*.

## Fail gates
Any new renderer/media owner, forced autoplay, wrong profile, missing title, Back precedence regression, silent account leakage, app-ID collision, 1%-sample shortcut mislabeling p99, staging writes to TV or undocumented external requests -> FAIL / BLOCKED. No approval inferred from code merge.
