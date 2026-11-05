# Prioritized native performance proposals

Review lenses: native rendering, embedded memory, input latency, forensic reproducibility. These are source-backed proposals, **not implemented native changes or measured improvements**. Base: `e5608cd053be5376a54a806129a332952dfabcef`. No new library is justified yet; reuse existing owners and locks.

## 1. First-use wallpaper preparation spikes — highest priority

**Evidence.** `Renderer::folded_image` selects a 2× wallpaper variant, then on cache miss synchronously calls `image::open`, `into_rgba8` and texture upload inside scene build (`src/renderer.rs:953–1035`). `Renderer::prepare` calls the same build path on the SDL thread after a frame (`1178–1186`; `src/main.rs:1841–1862`). Prewarm therefore moves work out of navigation but does not make it non-blocking. `image_load_ms` currently combines decode and upload. `prepare` advances `self.frame` and trims caches while restoring only visible stats; visible-page entries can become eviction candidates during hidden preparation.

**Smallest next measurement.** On the pinned desktop environment, use isolated preferences and existing `--profile-frames`/`--diagnostics`; compare a cold wallpaper first-use/navigation run with a warm run and record `image_ms`, interval p95/p99, compose/render/swap and prewarm logs. Do not call this TV performance. Add separate `prepare_ms`, `image_decode_ms`, `image_upload_ms`, wallpaper key and cache-hit counters before attempting a worker change.

**Bounded proposal after measurement.** Reuse the installed-artwork worker pattern: one bounded decode job per wallpaper generation, RGBA payload cap, cancellation on selection/visibility change, SDL-thread-only GL upload, retain old texture until replacement is ready. Protect the last visible cache generation during hidden prepare. Default OFF until A/B evidence.

**Negatives/acceptance.** Stale job cannot replace a newer wallpaper; hidden/closed session cannot upload; decode failure falls back without removing the old texture; no unbounded queue; no synchronous decode in the focus path; damage includes old/new wallpaper; p99 input-to-visible-call does not regress. Cache payload and RSS/PSS stay bounded where measurable.

## 2. Aggregate vector-cache accounting and eviction

**Evidence.** `vectors: HashMap<String, Option<Mesh>>` has no aggregate eviction (`renderer.rs:341`). Every frame recomputes count/bytes by iterating all meshes (`1478–1480`). `Mesh` owns a GL buffer and deletes it in `Drop` (`src/vector.rs:5–10,80–83`), so eviction is a GPU-resource lifetime operation, not just HashMap removal. Individual files are capped at 1,000,000 vertices, but the aggregate is not.

**Proposal.** Phase 1: incremental byte/count accounting on insert/remove, cache-hit/miss and eviction counters; no behavior change. Phase 2: default-OFF LRU/frame-generation eviction using a budget derived from measured active-set peak plus headroom—not an invented constant. Never evict a mesh referenced by the current visible batches; delete GL buffers only on the SDL thread after draw. Separate prepare generation from visible generation.

**Negatives/acceptance.** Eviction cannot delete a buffer still referenced by a batch; repeated navigation does not grow aggregate bytes without bound; reload after eviction is correct; failed loads remain bounded negative-cache entries; prepare does not evict the visible working set merely because stats were restored. Native tests and damage verification required.

## 3. Input-to-visible-focus diagnostics and p99

**Evidence.** `Profile` records post-swap call cadence and p95 only (`src/diagnostics.rs`). SDL events are dequeued in `main.rs:1218–1224`; focus changes and presentation are separate. There is no event-to-present association. Offline p99 is now derivable from the existing timeline via `research/scripts/analyze_native_diagnostics.py`; no native data was available to analyze.

**Proposal.** Add nearest-rank `p99_ms` beside p95 using the existing sorted-sample formula. For remote D-pad/OK and scripted focus changes, stamp `Instant::now()` at dequeue, assign a monotonic trace ID and target identity, and close the trace at the first swap call containing the changed scene. Report `input_dequeue_to_visible_call_ms`, coalesced/dropped traces and hidden-window exclusions. This is not photon latency and excludes time before dequeue unless SDL timestamp calibration is separately proven.

**Negatives/acceptance.** Hand-computed n=100 p99=99th ordered sample; warmup/capture exclusions unchanged; repeated key events do not overwrite an older pending trace incorrectly; focus restored by stale inventory is identified; no present means no fabricated latency; idle wakeups are counted separately from presentations. Keep raw timeline and sample counts.

## 4. Corrected default-OFF focus-depth candidate

**Evidence.** Patch SHA-256 `8230cce60f85db4965f0731e702216dbb5fe7442ee0a33ba4768f9dc0b24a257`. Isolated source-pinned gate passed forward check/apply, reverse check/apply, reverse-on-baseline rejection, double-apply rejection and stale-context rejection; application source remained byte-identical. See `PATCH-INTEGRITY.md`.

**Next native experiment.** After toolchain restoration, run the four supplied Rust tests plus existing focus/damage/pointer/Back regressions; compare unset versus exact `LUMA_FOCUS_DEPTH=1` with identical assets/preferences/scripts. Acceptance: default scene/draw parameters unchanged, only focused shadow changes, controls/hit rects unchanged, old/new shadow damage covered, no new cache/timer/persistent setting. Native/TV remains BLOCKED/NOT_RUN.

## 5. Real video — only after measurement infrastructure is proven

Keep the existing supported-player handoff as the baseline. Do not add a decoder/media plane until p99/input-latency/cache/memory-slope instrumentation and cleanup tests exist. Then follow the approval-gated plan in `../research/luma-audit/video-feasibility.md`: read-only API/library census, owner-owned unprotected fixture, separate-player control, and only separately approved plane/import probes. No DRM interception, system compositor mutation or protected-service inference.

## Ordering

1. Restore the manual reference environment; run original baselines unchanged.
2. Instrument/measure cold wallpaper and vector active set (no behavior change).
3. Add p99/focus-call traces and validate with synthetic + native unit tests.
4. Run the integrity-verified focus candidate as the smallest UI A/B.
5. Only then consider worker decode or vector eviction; video remains a later, separate gate.
