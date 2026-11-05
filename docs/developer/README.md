# Developer Guide

This section covers how to build, test, and contribute to Luma. It is written for new contributors and AI coding agents who need to work with this codebase.

## Contents

- [`build.md`](build.md) — Build from source (desktop and TV)
- [`toolchain.md`](toolchain.md) — Toolchain setup (Nix, Rust, Node, pnpm)
- [`testing.md`](testing.md) — Testing strategy and commands
- [`ci-cd.md`](ci-cd.md) — CI workflows and release process
- [`contributing.md`](contributing.md) — Contribution guidelines for agents and humans
- [`code-conventions.md`](code-conventions.md) — Coding conventions and style

## Quick start

```sh
# With Nix (recommended — supplies Rust 1.93, Node 24, pnpm 10, SDL2)
nix develop

# Without Nix — install manually: Rust 1.88+, Node 22+, pnpm 10, SDL2, pkg-config
pnpm install --frozen-lockfile
pnpm assets
pnpm dev                    # Desktop preview (no TV needed)
```

## Where to start

| If you want to...       | Read first                                                                                                 |
| ----------------------- | ---------------------------------------------------------------------------------------------------------- |
| Understand the codebase | [`architecture/system-overview.md`](../architecture/system-overview.md)                                    |
| Make a code change      | [`contributing.md`](contributing.md)                                                                       |
| Run tests               | [`testing.md`](testing.md)                                                                                 |
| Build for TV            | [`build.md`](build.md)                                                                                     |
| Add a new feature       | [`contributing.md`](contributing.md) + [`architecture/component-map.md`](../architecture/component-map.md) |

## Constraints for all changes

1. **Never block the SDL/rendering thread** — background work on workers only.
2. **Single navigation and state owner** — `src/state.rs` owns all state and focus.
3. **No new services or dependencies** — reuse existing workers and patterns.
4. **Experimental functionality default OFF** — feature-gated with `#[cfg(feature = "...")]`.
5. **Fail closed** — optional integrations fail without crashing.
6. **No physical TV operations** — no root, firmware, Home, or system changes without authorization.
7. **No fake measurements** — never claim hardware measurements without actual test execution.
