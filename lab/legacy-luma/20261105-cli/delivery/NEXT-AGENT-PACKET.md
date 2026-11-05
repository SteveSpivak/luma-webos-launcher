# Next-agent packet: working faster in this checkout

**Read this before re-deriving anything.** This packet exists so a new agent
starting from this exact checkout does not repeat finished work, does not
re-learn the environment's rough edges the hard way, and has one CLI for the
orientation/forensics/math tasks that previously needed ad hoc commands.

**Base:** `e5608cd053be5376a54a806129a332952dfabcef`. **This packet's commit
context:** branch `arena/0bee657b-lg-luma` only — never `main`, never the
reference repo. Everything below is read-only tooling; none of it installs
dependencies, builds native code, or contacts a TV.

## 0. The one command to run first

```
python3 -B research/scripts/luma_cli.py status
```

One JSON blob: current HEAD/branch, manifest summary (file count, candidate
patch state, native-validation status, pinned reference-comparison commit),
every blocker from `BLOCKERS.json`, the receipt index (count + any missing),
whether any protected path has drifted from `e5608cd0…`, and a **live** run of
`research/tests` (not a cached number — it actually runs the suite). Exit 0
only if tests pass and no protected path changed.

## 1. The CLI: `research/scripts/luma_cli.py`

A single entrypoint over existing scripts/modules — it does not duplicate
their logic, it imports or subprocesses them. Run `--help` or any
subcommand `--help` for full flags.

| Command | What it answers | Notes |
|---|---|---|
| `status` | "Is everything still green? What's blocked?" | Dashboard above. |
| `map` | "What does the whole tree look like?" | Per-directory file/extension counts, doc list, script list — from `git ls-tree`, so it's accurate at any commit, not just the working copy. |
| `docs` | "What docs exist and do their relative links resolve?" | Heading index of every `delivery/*.md` and `research/luma-audit/*.md`, plus a broken-relative-link gate (exit 1 if any link is dead). Run after writing or moving any doc. |
| `components` | "What Rust modules exist, and how do they relate to the pinned reference fork?" | Classifies every `.rs` file (rendering / media / connectivity / platform / runtime / tests / other) by filename pattern. If `research/audit/reference-launcher-facts.json` exists, layers in the OBSERVED shared/only-ours/only-reference counts from the already-completed comparison — it does **not** re-clone or re-derive that comparison. |
| `review` | "Did this change touch anything protected?" | `git diff --stat` + protected-path flags between two revisions (default: audit base → `HEAD`). Add `--patch-gate` to also run `check_patch_integrity.py`. Exit 1 if any protected path changed. |
| `math <fn> [args] [--kw k=v]` | "What does this shadow/spring/bandwidth number actually come out to?" | Calls any pure function in `reference_launcher.py` by name. `math --list` prints every function with its signature and one-line doc. Every result is labelled `MODEL` — arithmetic from the numbers you gave it, never a device measurement. |
| `gates` | "What native tools are missing?" | Thin wrapper on `native_preflight.py`. Exit 1 is the expected state until a real toolchain exists; this **never installs anything**. |
| `forensics --external-repo PATH [--external-rev SHA]` | "How does an already-cloned repo compare to ours, blob for blob?" | Generic version of the Luma-specific reference comparison — works against *any* local git clone (e.g. a future `continue-watching` reference, a newer launcher fork). Refuses to compare against a moving ref if you pin `--external-rev`. It does not clone anything itself — point it at a clone you already made. |
| `test [--pattern P] [--verbose]` | Run `research/tests` | Same invocation the rest of this project uses (`unittest discover` from the repo root — see the cwd gotcha below). |

### Math/physics quick reference

The functions behind `math` (in `research/scripts/reference_launcher.py`,
despite its reference-comparison-sounding name — they are generic UI motion
and raster-cost primitives, not specific to any one repo):

- **Shadow/raster cost**: `shadow_quad`, `penumbra_ring`, `damage_area`,
  `zoom_area_factor`, `depth_index`, `softness`, `penumbra_span`, `contrast`,
  `composite_alpha`, `grid_shadow_area`.
- **Motion**: `pop` (focus spring value at normalized time k), `pop_peak_k`,
  `pop_peak`, `equivalent_damping`, `pop_settle_k`, `chase_rate`, `chase_tau`,
  `chase_settle`.
- **Bandwidth**: `rgba_bytes`, `fill_bytes`, `bandwidth_gbs`.

Example — before touching any focus/shadow constant, model its cost first:

```
python3 -B research/scripts/luma_cli.py math shadow_quad 256 154.4 42
python3 -B research/scripts/luma_cli.py math pop_peak --kw decay=5 --kw freq=10
```

These are arithmetic sanity checks, not a substitute for the native A/B in
`delivery/NATIVE-VALIDATION.md` once a toolchain exists.

## 2. Documentation architecture (what to read, in order)

1. `delivery/SCORECARD.md` — shortest path to current status.
2. `delivery/manifest.json` — exact SHAs/hashes/exits/evidence classes.
3. `delivery/HANDOFF.md` — narrative handoff; "Read first" list for the base audit.
4. `research/luma-audit/REFERENCE-LAUNCHER-COMPARISON.md` — the sibling-fork
   comparison (forensics, components, focus math, docs-vs-code, adopt/defer/reject).
5. `delivery/PATCH-INTEGRITY.md`, `delivery/BUILD-ENVIRONMENT.md`,
   `delivery/NATIVE-VALIDATION.md`, `delivery/PERFORMANCE-PROPOSALS.md`,
   `delivery/BLOCKERS.json`, `delivery/rollback.md`.
6. `research/luma-audit/` — `architecture.md`, `capability-ledger.json`,
   `rendering-performance.md`, `ux-settings.md`, `video-feasibility.md`,
   `device-validation-plan.md`, `references.md`, `focus-experiment.md`.

Run `python3 -B research/scripts/luma_cli.py docs` any time to regenerate the
heading index and confirm no relative link between these files is dead.

## 3. Code review workflow

1. `python3 -B research/scripts/luma_cli.py review` before and after any
   change. It must report `protected_clean: true` unless the change is an
   intentional, approved source edit.
2. For a candidate patch specifically, `check_patch_integrity.py` (or
   `review --patch-gate`) proves forward/reverse apply and byte-identical
   source in an external non-Git scratch directory — see
   `delivery/PATCH-INTEGRITY.md` for why that isolation matters (the original
   patch-apply failure mode is recorded there so it is not rediscovered).
3. Run `python3 -B research/scripts/luma_cli.py test` (or the plain
   `unittest discover` command below) before any commit. 76 tests currently
   pass; if your change doesn't add or fix a test, treat that as a signal
   you've skipped the project's own convention (every delivered script here
   has hand-computed, not loosened, test coverage).
4. After any new file under `research/` or `delivery/`, regenerate the
   manifest: `python3 -B research/scripts/build_manifest.py
   --implementation-commit <current HEAD>` and record the new aggregate hash.

## 4. Forensics: comparing against another repository

Two tools, different scope:

- **This pinned comparison is already done.** `funnymataleao/luma-webos-launcher`
  @ `40994fc144b5af481056d14e2fb93304aa1e2c82` (MIT, sibling fork of
  `ecklf/lg-luma`, not a successor) was cloned read-only outside the checkout
  and compared against audit base `e5608cd0…`. Results:
  `research/audit/reference-launcher-facts.json` (machine-readable) and
  `research/luma-audit/REFERENCE-LAUNCHER-COMPARISON.md` (narrative). Do not
  repeat this clone/compare unless you need a different pin or the facts file
  is missing — `luma_cli.py components` already surfaces its headline counts.
- **For any other repository** (a later Luma fork, a continue-watching
  reference implementation, etc.): clone it yourself, read-only, outside this
  checkout, pin its exact commit, then run
  `luma_cli.py forensics --external-repo <clone path> --external-rev <sha>`.
  It reports shared/identical/changed/only-ours/only-theirs blob counts —
  nothing more, nothing copied in. If you need Luma-specific detail (shadow
  constants, focus math, cache budgets) beyond a blob diff, use
  `compare_reference_launcher.py` as the template — it is built the same way
  and its functions (`tree_entries`, `module_class`, `shadow_calls`) are
  already generic enough to reuse directly.

### Already-researched continue-watching prior art (read before building anything)

`NuvioMedia/NuvioTVSmart` @ `657c8a308d0c36aca1625a5e9293b3ba651f017b` was
already read for UX behavior (not code import — it's GPL-3.0, a different
license, and nothing from it is in this tree). Recorded findings, in
`research/luma-audit/references.md`: late focus requires no pending
interaction/suppression/prior-application state; focused identity must
survive list reconstruction; an "ambient" autoplay/preview policy requires
*actual* unpaused, non-loading playback state, not an assumed one; a
screen-level back/router must consume Back before any parent handler; a
poster/preview flow needs a cancelable token plus a delay plus revalidation
against the currently focused node (to avoid a stale fetch painting over a
now-different focus target). These are **behavior requirements to translate
into native Rust state machines**, not UI/CSS to port — this checkout has no
DOM/browser layer, and the standing instruction is to keep it that way.

## 5. Getting ready for a "continue watching" feature — what exists, what's next

**Not implemented. This section is a map, not a plan to execute unattended.**

What already exists that a continue-watching feature would sit on:
- `src/focus_experiment.rs` + the `LUMA_FOCUS_DEPTH` candidate pattern in
  `delivery/patches/focus-depth.patch` is the template for *any* new
  default-OFF, environment-gated experiment: isolated module, exact
  three-file diff scope enforced by `check_patch_integrity.py`'s
  `validate_scope()`, reversible, red-test-first.
- `research/luma-audit/focus-experiment.md` documents the process that
  produced it — reuse that process, don't invent a new one.
- The reference fork's `only_reference` modules (41 of them — jellyfin,
  plex, moonlight, player, library, movie, album, music, stacks, mini,
  widgets, etc., full list in `reference-launcher-facts.json`'s
  `components` array) show one architecture for this kind of feature set,
  but they are **their design, not a spec** — see the comparison report's
  adopt/defer/reject section before copying any of it.
- Nuvio's late-focus/ambient/poster-token behaviors above are the closest
  prior art for "continue watching" specifically (resuming a focus/preview
  state correctly across list changes).

Before writing any continue-watching code: run `luma_cli.py status` and
`luma_cli.py components` to see current module boundaries, write a red test
for the new module under `research/tests/` the way `test_candidate_patch.py`
does, keep it default-OFF and isolated to new files where possible, and run
the same forward/reverse integrity gate pattern before claiming it applies.
Native rendering/behavioral proof is still B01-blocked until a toolchain
exists — don't claim visual or performance results without it.

## 6. Environment gotcha: the sandbox can reset local git history mid-session

This happened twice in this session. Symptom: `git log` suddenly shows only
the base commit (`e5608cd0…`), but your new *untracked* files are still on
disk. **The remote branch is not affected.** Recovery, always safe because
`origin/arena/0bee657b-lg-luma` is the source of truth:

```
git fetch origin refs/heads/arena/0bee657b-lg-luma
git reset --hard FETCH_HEAD
git status --porcelain   # confirm your untracked work survived
```

Do this *before* any new commit attempt — committing on top of a
reset-to-base HEAD creates a second, divergent history on the same branch
name. Never push until `git log --oneline -3` shows your expected ancestor
chain.

## 7. Standing rules that still apply (do not relitigate these)

- Branch only: `arena/0bee657b-lg-luma`. Never `main`. Never push to
  `funnymataleao/luma-webos-launcher` (read-only reference).
- No automatic dependency installation, no native build, no physical-TV
  contact, no Home/boot-hook/firmware/DNS/media-protection/system-service
  changes.
- No file copies from any external repo into this checkout, no proprietary
  Apple code/assets, no DRM bypass, no protected-stream interception.
- Every experiment: bounded, default-OFF, red test first, deterministic
  rollback proof, no persistent setting without a tested migration.
- Report actual command exits; never rewrite a known-failing baseline to
  pass; stop and report after two repeated failures instead of retrying.
- Unavailable companion repos (`nuvio-perf-lab`, `LG-TV`,
  `lg-webos-firmware-lab`) are BLOCKED; do not retry them.
- Any performance/speed claim from a third-party repo's docs/README stays
  labelled as their claim, not evidence, until independently measured here.
