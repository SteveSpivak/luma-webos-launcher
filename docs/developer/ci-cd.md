# CI and Release Process

## CI workflow (`.github/workflows/ci.yml`)

The repository has a single CI workflow: `.github/workflows/ci.yml`. There is no separate `release-pr.yml` or `changeset-status.yml` workflow.

**Triggers:** Push to `main`, tags `v*`, pull requests, workflow dispatch.

**Jobs:**

| Job | Purpose |
|---|---|
| `build` | Rust checks, rendering, native package |
| `release` | Publish release and Homebrew feed (tags `v*` or manual dispatch from `main`) |

**Build job steps:**
1. Checkout, setup Node/pnpm
2. Install dependencies (`libsdl2-dev`, `pkg-config`, `woff2`, `python3-fonttools`, `libgl1-mesa-dri`, `xvfb`, `xauth`)
3. Check formatting (`pnpm format:check` → `cargo fmt --all -- --check` and `oxfmt --check .`)
4. Lint (`pnpm check` → version check, oxlint, and `cargo clippy --locked --workspace --all-targets --all-features -- -D warnings`)
5. Run unit tests (`pnpm test` → release, home, icons tests plus `cargo test --locked --workspace --all-features`)
6. Generate native assets (`pnpm assets`)
7. Desktop rendering + mocked weather (`xvfb-run -a -s '-screen 0 1920x1080x24' pnpm test:smoke`)
8. Set up the webOS SDK (`pnpm sdk`)
9. Cross-build ARM + IPK + Homebrew feed (`pnpm build`, `node tools/package.mjs`, `node tools/repository.mjs`)
10. Upload release artifacts (`dist/*.ipk`, `dist/*.manifest.json`, `dist/sha256sums`, `dist/repo.json`, `dist/description.html`, `dist/player-description.html`, `dist/app-icon-large.png`)
11. Upload native rendering diagnostics (`.build/*.png`, `.build/*-render.json`)

**Release job:** Triggers on `v*` tag push or manual workflow dispatch from `main`. Downloads the `luma-release` artifact and publishes to GitHub Release + Homebrew feed.

## Changesets

```sh
pnpm changeset
```

- Select package: `lg-luma`
- Choose bump: patch / minor / major
- Describe the change
- Commit generated file under `.changeset/` with the PR

**Bump rules:**
- `patch` — backward-compatible fixes
- `minor` — backward-compatible features
- `major` — breaking changes

Documentation-only and maintenance PRs can omit changesets.

## Publishing constraints

- Publish is triggered by a `v*` tag push to `main` or manual workflow dispatch from `main`
- The commit must pass CI (format, clippy, tests, native packaging)
- Ordinary merges and unmerged PRs do not publish
- To retry a failed publication, rerun the original CI run for the merged version PR's main-branch commit

## PR requirements

- Draft PR only — never merge automatically
- Changeset for code/behavior changes
- CI must pass (format, clippy, tests, build)
- Documentation updated for changed functionality
- Tests added for new features

## Current CI status

GitHub Actions provides Rust 1.93 via `dtolnay/rust-toolchain@1.93.0`. The sandbox does not have a local Rust toolchain, so `cargo fmt`, `cargo clippy`, and `cargo test` cannot be run here. Native CI results must be obtained from GitHub Actions. Do not claim native compilation, Clippy, tests, or ARM packaging passed unless the CI run has completed successfully.
