# CI and Release Process

## CI workflow (`.github/workflows/ci.yml`)

**Triggers:** Push to `main`, tags `v*`, pull requests, workflow dispatch.

**Jobs:**

| Job | Purpose |
|---|---|
| `build` | Rust checks, rendering, native package |
| `release` | Publish release and Homebrew feed (tags only) |

**Build job steps:**
1. Checkout, setup Node/pnpm
2. Install dependencies (`libsdl2-dev`, `pkg-config`, `woff2`, `python3-fonttools`, `libgl1-mesa-dri`, `xvfb`, `xauth`)
3. Check formatting (`pnpm format:check`)
4. Lint (`pnpm check`)
5. Run unit tests (`pnpm test`)
6. Generate native assets (`pnpm assets`)
7. Desktop rendering + mocked weather (`xvfb-run -a pnpm test:smoke`)
8. Setup webOS SDK (`pnpm sdk`)
9. Cross-build ARM + IPK + Homebrew feed (`pnpm build`, `pnpm package`)
10. Upload release artifacts

**Release job:** Triggers on `v*` tag push or manual dispatch. Uploads IPK, manifest, checksums, repo.json, description HTML, app icon.

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

## Release flow

1. Changesets merge into `main`
2. `.github/workflows/release-pr.yml` creates Version Packages PR on `changeset-release/main`
3. `pnpm version:release` updates `package.json`, `CHANGELOG.md`, `appinfo.json`, `Cargo.toml`, `Cargo.lock`
4. Review and merge Version Packages PR
5. Main-branch push + numeric version increase → publish job
6. Publish job: GitHub release + Homebrew feed

**Publishing constraints:**
- Only main-branch push associated with merged Version Packages PR
- Must pass CI, desktop smoke tests, native packaging
- Ordinary merges and unmerged PRs do not publish

## PR requirements

- Draft PR only — never merge automatically
- Changeset for code/behavior changes
- CI must pass (format, clippy, tests, build)
- Documentation updated for changed functionality
- Tests added for new features
