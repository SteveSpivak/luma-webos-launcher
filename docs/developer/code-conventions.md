# Coding Conventions

## Rust

- **Edition:** 2024
- **MSRV:** 1.88
- **Formatting:** `rustfmt` (default config, 100-char max width)
- **Lint:** `clippy -D warnings` on `--all-targets --all-features`
- **Feature gating:** Experimental features behind `#[cfg(feature = "...")]`, off by default
- **No `unwrap()` in production code:** Use proper error handling
- **No blocking on SDL thread:** All blocking work on dedicated workers
- **Error messages:** Truncated to 240 chars, include context (URI, operation)

## Documentation

- **Format:** Markdown
- **Model:** Diátaxis (tutorials, how-to, explanation, reference)
- **Diagrams:** Text-based (ASCII/Mermaid-compatible), no external image generation required
- **Source-backed:** Every claim traceable to specific files and functions
- **No speculation:** Runtime TV behavior documented only where verified

## Commit messages

```
type(scope): description

Body with motivation and context.

- Bullet point 1
- Bullet point 2
```

**Types:** feat, fix, docs, refactor, test, chore, perf, ci, build, revert

**Example:**
```
feat(nuvio): add title-to-detail launch integration

Add Request::NuvioLaunch, validate_nuvio_target(), and Effect::NuvioLaunch
behind the default-off `nuvio` feature flag.
```

## File organization

- **Source:** `src/` — one module per concern (see component map)
- **Tests:** `src/tests.rs` — unit tests, feature-gated where appropriate
- **Docs:** `docs/` — organized by audience and type (Diátaxis)
- **Assets:** `assets/` — SVGs, fonts, wallpapers, translations
- **Tools:** `tools/` — build, asset, packaging scripts
- **TV scripts:** `tv/` — root-only native Home integration

## What to avoid

- **Duplicate state machines:** `src/state.rs` is the single owner
- **Blocking the SDL thread:** Use workers for Luna, HTTP, image decode
- **New dependencies:** Prefer existing crates in `Cargo.toml`
- **Independent subsystems:** Reuse existing stacks, cards, artwork, navigation
- **Root-only behavior by default:** Root features are optional and gated
- **Fake measurements:** Never claim unexecuted test results as PASS
