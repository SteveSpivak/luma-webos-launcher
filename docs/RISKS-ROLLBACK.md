# Risks and Rollback — Nuvio Integration

## 1. Risks

| Risk | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|
| `clippy -D warnings` fails on `dead_code` for Nuvio constants in default builds | Low | Medium (CI failure) | Fixed: `NUVIO_APP_ID` and `NUVIO_NOT_INSTALLED` are `#[cfg(feature = "nuvio")]`. `app_not_installed()` is ungated so `player_not_installed()` compiles in default builds. | Mitigated |
| `validate_nuvio_target()` too restrictive (Nuvio uses non-TMDB IDs or different URL shape) | Medium | Low (easy to widen) | Function is small and isolated; can be extended to accept additional patterns without changing the launch contract. | Open |
| `getAppInfo` preflight adds latency on absent-app path | Low | Low | Only called after a launch error; mirrors existing web-player pattern (~6500ms timeout bounded). | Open |
| Focus not moved on Nuvio launch may confuse users expecting navigation | Low | Low | Intentional: Back out of Nuvio returns to same focus. Users can re-navigate. Documented in USER-FLOWS.md. | Accepted |
| Phase 1 is launch-only; no stack row or cards | N/A (by design) | N/A | Phase 2 will add stack source when Nuvio producer contract is authorized. Not a Phase 1 gap. | Accepted |
| Default builds affected by Nuvio feature | Low | High | `nuvio` not in `default = []`; all Nuvio code `#[cfg(feature = "nuvio")]`. Default builds unchanged. | Mitigated |
| No native build verification possible in sandbox | High (environmental) | Medium (Gate 1 unverified) | Documented as BLOCKED. Cannot claim PASS until toolchain available. | Environmental blocker |
| `cargo fmt` line-length violations (>100 cols) | Low | Low | All added lines verified ≤100 chars via source inspection. | Mitigated |
| Translation placeholder mismatch | Low | Low | `nuvioNotInstalled` has no placeholders; follows existing pattern. i18n unit test enforces placeholder consistency. | Mitigated |

## 2. Rollback procedures

### Immediate rollback (source revert)

```bash
# On the implementation branch
git checkout arena/5fe14abb-luma-webos-launcher

# Option A: revert both commits (preserves history)
git revert 6dc1886 3031417

# Option B: hard reset to baseline (destructive to this branch's commits)
git reset --hard 40994fc

# Push the rollback
git push origin arena/5fe14abb-luma-webos-launcher

# Close the draft PR
gh pr close 2
```

### Verify rollback

```bash
# Default build must compile unchanged
cargo build --locked
# Expect: exit code 0

# All pre-existing tests pass
cargo test --locked
# Expect: exit code 0

# Tree is clean (no Nuvio references remain)
git status --short
# Expect: nothing to commit
```

### What rollback removes

- `Cargo.toml` `nuvio` feature
- `src/platform.rs`: `NUVIO_APP_ID`, `NUVIO_NOT_INSTALLED`, `Request::NuvioLaunch`, `validate_nuvio_target()`, `nuvio_launch_params()`, worker arm
- `src/state.rs`: `Effect::NuvioLaunch`, `Target::NuvioLaunch`, `activate()` arm
- `src/main.rs`: `Effect::NuvioLaunch` effect arm, `NUVIO_NOT_INSTALLED` error handling
- `assets/messages.json`: `nuvioNotInstalled` translations
- `src/tests.rs`: `mod nuvio` test module

### What rollback preserves

- All existing Luma functionality (Jellyfin, Plex, Moonlight, widgets, motion, wallpaper, etc.)
- Default builds completely unaffected
- `main` branch untouched

## 3. Forward progress conditions

Phase 1 is considered complete when:
1. All source changes committed and pushed ✅ (done)
2. Draft PR #2 open ✅ (done)
3. Native build + tests pass (BLOCKED — no toolchain)
4. Rollback verified (deferred until build possible)

Phase 2 (Continue Watching) can only start when:
1. Gate 1 is satisfied (native build + tests pass)
2. A Nuvio owner authorizes a Continue Watching producer contract
3. The contract defines the publish schema, authentication, and refresh cadence

## 4. What must NOT be rolled back or changed

- `main` branch — never modified
- Other agents' work on other branches — never touched
- Existing advanced Luma features — preserved
- Physical TV, firmware, root services — never accessed