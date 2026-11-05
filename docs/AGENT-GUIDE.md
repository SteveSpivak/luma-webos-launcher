# AI Agent Guide — Working with the Luma Codebase

This guide is for AI coding agents that need to make changes to Luma. It explains how to understand, navigate, modify, test, and document this codebase safely.

## 1. Core principles (read first)

1. **Inspect before changing.** Never infer behavior from file names. Read the actual owner files.
2. **Reuse before adapting.** Adapt before creating. Do not create independent subsystems when existing owners can handle the requirement.
3. **Smallest testable unit.** Implement one independently testable change at a time.
4. **Never block the SDL/rendering thread.** All blocking work (Luna, HTTP, image decode) runs on dedicated workers.
5. **Single state owner.** `src/state.rs` owns all navigation, focus, and state. Do not create parallel state machines.
6. **Experimental functionality default OFF.** All new features are `#[cfg(feature = "...")]` gated and off by default.
7. **Fail closed.** Optional integrations fail safely when the service is absent. Never crash the launcher.
8. **No physical TV operations.** No root, firmware, Home, system settings, or device changes without separate authorization.
9. **No fake measurements.** Never claim unexecuted tests as PASS. Never report calculated values as measured.
10. **Stop after two repeated failures.** If the same test fails twice, stop and reassess.

## 2. Repository map for agents

| Question | Where to look |
|---|---|
| What does the project do? | `docs/overview.md`, `README.md` |
| How is the system architected? | `docs/architecture/system-overview.md` |
| What components exist and who owns them? | `docs/architecture/component-map.md` |
| How does data flow through key scenarios? | `docs/architecture/data-flows.md` |
| What is the app lifecycle? | `docs/architecture/lifecycle.md` |
| How do users interact with each screen? | `docs/user-guide/` |
| How do I build and test? | `docs/developer/build.md`, `docs/developer/testing.md` |
| How do I contribute? | `docs/developer/contributing.md` |
| What are the coding conventions? | `docs/developer/code-conventions.md` |
| What preferences exist? | `docs/reference/preferences.md` |
| What app IDs are used? | `docs/reference/app-ids.md` |
| What terms mean what? | `docs/reference/glossary.md` |
| What is the Nivío integration? | `docs/nuvio/` (CHARTER.md, ARCHITECTURE.md, etc.) |
| What webOS integration exists? | `docs/platform/` |

## 3. Source file ownership quick reference

| Concern | Primary owner file | Secondary files |
|---|---|---|
| App launch to TV | `src/platform.rs` | `src/luna.rs` |
| UI state & navigation | `src/state.rs` | `src/main.rs` |
| Rendering scene | `src/view.rs` | `src/renderer.rs` |
| Stack rows (Home content) | `src/stacks_view.rs` | `src/stacks.rs` |
| App tiles (Apps grid) | `src/view.rs::tile()` | `src/branding.rs`, `src/app_artwork.rs` |
| Jellyfin media | `src/jellyfin.rs` | `src/media.rs` |
| Plex media | `src/plex.rs` | `src/media.rs` |
| Moonlight games | `src/moonlight.rs` | `src/stacks.rs` |
| Smart Home | `src/smart_home.rs` | `src/smart_home_ws.rs` |
| Widgets | `src/widgets.rs` | `src/widgets_state.rs`, `src/widgets_view.rs` |
| Video wallpaper | `src/hw_wallpaper.rs` | `src/aerial_video.rs` |
| Preferences | `src/model.rs::Preferences` | `src/storage.rs` |
| Translations | `src/i18n.rs` | `assets/messages.json` |
| Tests | `src/tests.rs` | `src/app-artwork-tests.rs`, `src/weather-tests.rs` |

## 4. How to add a new feature (agent workflow)

### Step 1: Understand (do not skip)

```bash
# Read the architecture
cat docs/architecture/system-overview.md
cat docs/architecture/component-map.md

# Read the relevant user flow
cat docs/user-guide/navigation.md

# Inspect the source files you will modify
# Do not guess — read the actual code
```

### Step 2: Plan

1. Identify the owner file(s) for your change.
2. Determine if you need a new feature flag (`#[cfg(feature = "...")]`).
3. Identify what tests need to be added (positive + negative).
4. Identify what documentation needs to be updated.
5. Write a plan (even a short one) before coding.

### Step 3: Implement

1. Make the smallest independently testable change.
2. Reuse existing patterns (workers, effects, targets, stack items).
3. Keep all new code feature-gated if experimental.
4. Do not block the SDL thread.
5. Do not duplicate state.

### Step 4: Test

```bash
cargo fmt --all -- --check
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
cargo test --locked --workspace --all-features
```

Add tests for:
- Happy path (positive)
- Invalid inputs (negative)
- Missing service / absent app
- Duplicate requests
- Focus preservation / Back behavior

### Step 5: Document

1. Update `docs/` if the change affects users or architecture.
2. Add a changeset for code/behavior changes (`pnpm changeset`).
3. Update this guide if the contribution process changes.

### Step 6: Submit

1. Open a draft PR (never merge automatically).
2. Address review feedback.
3. Ensure CI passes before merge.

## 5. Anti-patterns (do not do these)

| Anti-pattern | Why | Correct approach |
|---|---|---|
| Creating a new state machine | `src/state.rs` is the single owner | Add to existing `Effect`/`Target` enums |
| Blocking SDL thread with HTTP/Luna | Freezes the UI | Use platform worker or existing service worker |
| Adding a new dependency when one exists | Increases build size, maintenance | Check `Cargo.toml` first |
| Hard-coding TV behavior | Not portable, breaks desktop | Use `webos` feature flag and desktop fallbacks |
| Claiming untested behavior as verified | False confidence | Run tests or mark as BLOCKED |
| Modifying root/system without authorization | Violates project policy | Document as BLOCKED, request authorization |
| Merging PR automatically | Bypasses review | Use draft PR, manual merge |
| Creating independent UI framework | Duplicates `stacks_view.rs`, `view.rs` | Reuse existing card rendering |

## 6. Writing tests

### Test structure

```rust
#[cfg(feature = "myfeature")]
mod myfeature {
    use super::*;

    #[test]
    fn test_name() {
        // Arrange
        // Act
        // Assert
    }
}
```

### What to test for every new feature

- [ ] Valid inputs produce expected output
- [ ] Invalid inputs are rejected with clear errors
- - Missing service / absent app handled gracefully
- [ ] Duplicate requests are blocked
- [ ] Focus is preserved where expected
- [ ] Back behavior is correct
- [ ] Default builds are unchanged (feature-gated code compiles out)

### Negative test examples

```rust
// Invalid input rejected
assert!(validate_input("bad input").is_err());

// Missing service handled
assert_eq!(handle_missing_service(), Err("Service not available"));

// Duplicate blocked
state.launching = true;
assert!(state.activate().is_empty());
```

## 7. Documentation updates

When your change affects users or architecture, update:

| Change type | Docs to update |
|---|---|
| New user-facing feature | `docs/user-guide/` + `docs/overview.md` |
| New component or architecture change | `docs/architecture/` |
| New build/test procedure | `docs/developer/` |
| New TV integration | `docs/platform/` |
| New preference or setting | `docs/reference/preferences.md` |
| New app ID | `docs/reference/app-ids.md` |
| New term | `docs/reference/glossary.md` |
| Contribution process change | `docs/developer/contributing.md`, this guide |

## 8. Review checklist (self-review before PR)

```
[ ] I read the owner files before changing them
[ ] I reused existing components before creating new ones
[ ] My change is the smallest testable unit
[ ] No blocking work on the SDL thread
[ ] `src/state.rs` remains the single state owner
[ ] Experimental code is feature-gated and default-off
[ ] The integration fails closed when services are absent
[ ] I added positive and negative tests
[ ] I ran cargo fmt, clippy, and tests locally (or documented BLOCKED)
[ ] I updated documentation if user-facing or architectural
[ ] I added a changeset for code/behavior changes
[ ] Rollback instructions are documented
[ ] I did not claim unexecuted tests as PASS
[ ] I did not fake hardware measurements
[ ] I did not modify physical TV, firmware, or system settings
```

## 9. When to stop and request human input

- You need to operate on a physical TV, firmware, or root services
- You need to change LG Home, boot behavior, or system settings
- You need to add a new dependency that duplicates existing functionality
- You are unsure whether a change requires authorization
- The same test fails twice (stop after two repeated failures)
- You need to create a new rendering system or navigation engine

## 10. Alignment with other agents

All agents work on the same branch (`arena/5fe14abb-luma-webos-launcher`). Before starting:

1. Read the current branch state: `git log --oneline -5`, `git status --short`
2. Read the open PR: `gh pr list --state open`
3. Read this guide and the architecture docs
4. Coordinate changes to avoid conflicts on shared files (`src/state.rs`, `src/main.rs`, `src/platform.rs`)
5. Do not force-push, reset, or overwrite other agents' work
6. Do not rename the branch
