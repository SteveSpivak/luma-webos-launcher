# Testing

## Test types

| Type              | Location                   | Runs on          |
| ----------------- | -------------------------- | ---------------- |
| Rust unit tests   | `src/tests.rs`             | Desktop (no TV)  |
| App artwork tests | `src/app-artwork-tests.rs` | Desktop          |
| Weather tests     | `src/weather-tests.rs`     | Desktop          |
| Desktop smoke     | `tests/*.mjs`              | Desktop + xvfb   |
| Icon smoke        | `tests/*.mjs`              | Desktop          |
| Brand smoke       | `tests/brands-smoke.mjs`   | Desktop renderer |

## Rust tests

```sh
cargo test --locked --workspace --all-features
```

**Includes:** All unit tests, including feature-gated tests (e.g. Nivío launch tests behind `--features nuvio`).

**No TV required:** Tests use `demo_inventory()` and mocked data. No live TV calls.

## Desktop smoke tests

```sh
pnpm test:smoke
```

Runs: `tests/smoke.mjs`, `tests/brands-smoke.mjs`, `tests/weather-smoke.mjs`, `tests/translations-smoke.mjs`.

**Requires:** Desktop display or `xvfb-run -a`.

## Individual test commands

```sh
# Format check
cargo fmt --all -- --check
pnpm format:check

# Clippy
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
pnpm check

# All tests
cargo test --locked --workspace --all-features
pnpm test

# Release tooling tests
pnpm test:release

# Home splash tests
pnpm test:home

# Icon tests
pnpm test:icons

# Weather tests
pnpm test:weather

# Translations tests
pnpm test:translations

# Brands smoke (renders all brand cards)
pnpm test:brands
```

## Test invariants

- Every message has all 5 languages, no empty values
- Every translation preserves English message placeholders
- Localization keeps user-provided names intact
- SVG directory, curated catalogue, and demo inventory stay aligned
- No missing glyphs, images, or failures in rendered output

## CI test flow

1. `pnpm format:check`
2. `pnpm check` (Clippy + lint)
3. `pnpm test` (unit tests)
4. `pnpm assets` (generate native assets)
5. `xvfb-run -a pnpm test:smoke` (desktop rendering)
6. `pnpm build` + `pnpm package` (ARM cross-build + IPK)

**Note:** Host CI cannot prove hardware compatibility, small-text quality, or presentation frame rate. Those require real TV testing.

## What cannot be tested without a TV

- Native ARM webOS build execution
- Actual Luna service calls
- TV hardware frame pacing
- Real Jellyfin/Plex server connections
- Home Assistant WebSocket from TV
- Physical remote input
