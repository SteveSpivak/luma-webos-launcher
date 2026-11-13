# Verified Facts Report — Luma Documentation

Generated during the whole-project documentation quality gate. All facts below
were verified against the actual repository state on branch
`arena/5fe14abb-luma-webos-launcher` at commit `59dcced`.

## Scope

- Whole-project documentation covers Luma **as-is** (before Nivío additions).
- Nivío docs remain in `docs/` at top level, clearly marked as integration-scoped.
- 46 markdown documentation files total: 36 whole-project + 10 Nivío-scoped.
- 22 screenshot JPG files in `docs/screenshots/` — all referenced and resolved.

## Verified: Documentation Structure

| Check | Result |
|---|---|
| Every doc subdirectory has a `README.md` index | Pass |
| `docs/README.md` is the index for all docs | Pass |
| All 46 markdown files committed and pushed | Pass |
| Draft PR #2 open against `main` | Pass |

## Verified: Links and References

| Check | Result |
|---|---|
| All relative Markdown links resolve | Pass (0 broken) |
| All source-file references (`src/*.rs`) resolve | Pass (0 broken) |
| All screenshot references (`docs/screenshots/*.jpg`) resolve | Pass (0 broken) |
| No references to non-existent CI workflows | Pass |
| No destructive `git reset --hard` in rollback guidance | Pass |
| `docs/nuvio/` reference replaced with top-level Nivío docs | Pass |
| `../../releases/latest` link fixed to full GitHub URL | Pass |
| `.tsx` references corrected to `.rs` where applicable | Pass |

## Verified: Source Files Referenced in Docs

The following source files are referenced in documentation and exist in the repo:

`src/main.rs`, `src/state.rs`, `src/view.rs`, `src/renderer.rs`, `src/platform.rs`,
`src/stacks.rs`, `src/stacks_view.rs`, `src/jellyfin.rs`, `src/plex.rs`, `src/moonlight.rs`,
`src/smart_home.rs`, `src/smart_home_settings_view.rs`, `src/smart_home_ws.rs`,
`src/widgets.rs`, `src/media.rs`, `src/app_artwork.rs`, `src/branding.rs`, `src/hw_wallpaper.rs`,
`src/i18n.rs`, `src/luna.rs`, `src/model.rs`, `src/storage.rs`, `src/weather-service.rs`,
`src/tests.rs`, `src/typography.rs`, `src/ui_sound.rs`, `src/vector.rs`,
`assets/messages.json`, `tv/home.sh`, `tv/home.cjs`, `tv/autostart.sh`, `tv/luma-wake.sh`,
`tv/read-app-icon.cjs`, `Cargo.toml`, `Cargo.lock`, `appinfo.json`, `flake.nix`, `flake.lock`

## Verified: Not Found (Expected — on Nivío branch or TV-only)

| Item | Why not in repo | Where it lives |
|---|---|---|
| `src/nuvio.rs` | Nivío consumer service not yet implemented on main | Nivío branch `research/arena-nuvio-integration-kit-20261105` |
| `tv/64-luma-home` | TV-side systemd boot hook (not a repo file) | TV filesystem `/etc/init.d/` |
| `tv/65-luma` | TV-side systemd boot hook (not a repo file) | TV filesystem `/etc/init.d/` |

## Verified: CI and Toolchain

| Check | Result |
|---|---|
| Single CI workflow: `.github/workflows/ci.yml` | Confirmed |
| No `release-pr.yml` or `changeset-status.yml` workflows | Confirmed (removed from docs) |
| Rust toolchain: CI uses `dtolnay/rust-toolchain@1.93.0` | Confirmed in ci.yml |
| Sandbox: no Rust toolchain, no pnpm | Confirmed — CI formatting (rustfmt/cargo fmt) cannot run locally |
| Release flow: `v*` tag push or manual dispatch from main | Confirmed in ci.yml |

## Verified: Rollback Guidance

| File | Change |
|---|---|
| `docs/ARCHITECTURE.md` | `git reset --hard 40994fc` removed; `git revert` only |
| `docs/MEASUREMENT.md` | `git reset --hard 40994fc` removed; `git revert` only |
| `docs/RISKS-ROLLBACK.md` | `git reset --hard 40994fc` removed; `git revert` only |

## Verified: Agent/Branch Ownership

| File | Change |
|---|---|
| `docs/AGENT-GUIDE.md` | "All agents work on same branch" → isolated worktree/branch ownership |
| `docs/ALIGNMENT.md` | "All agents work on same branch" → isolated feature branches/worktrees |

## Tools Created

| Tool | Purpose |
|---|---|
| `tools/validate_docs.py` | Stdlib-only documentation validator (links, source refs, screenshots, rollback, workflows) |
| `tools/test_validate_docs.py` | Negative test suite (9 tests, all passing) |
| `tools/generate_doc_inventory.py` | Generates `doc-inventory.json` and `doc-ownership.csv` |
| `tools/doc-inventory.json` | Machine-readable documentation inventory (46 docs) |
| `tools/doc-ownership.csv` | Doc-to-source ownership matrix (339 mappings) |

## Limitations

- No Rust toolchain in sandbox — `cargo fmt`/`rustfmt` cannot be run to verify Rust source formatting.
- No pnpm in sandbox — Node.js smoke tests cannot be run locally.
- Physical TV operations blocked by policy — no ARM webOS build or on-device testing attempted.
- Documentation validator does not check Markdown heading levels, alt text on images, or internal anchor validity.
