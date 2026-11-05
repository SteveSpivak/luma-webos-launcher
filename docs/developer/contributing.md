# Contribution Guidelines

## For human contributors

1. **Fork and branch:** Create a feature branch from `main`. Never push directly to `main`.
2. **Implement:** Make the smallest independently testable change. Reuse before adapting, adapt before creating.
3. **Test:** Add tests for new functionality. Run `cargo test`, `cargo clippy`, `cargo fmt`.
4. **Document:** Update documentation for changed functionality.
5. **Changeset:** Add a changeset for code/behavior changes (`pnpm changeset`).
6. **Draft PR:** Open a draft pull request. Never merge automatically.
7. **Review:** Address review feedback. CI must pass before merge.

## For AI coding agents

### Before writing code

1. **Read the architecture:** [`architecture/system-overview.md`](../architecture/system-overview.md), [`architecture/component-map.md`](../architecture/component-map.md)
2. **Read the relevant user flow:** [`user-guide/`](../user-guide/README.md)
3. **Inspect source:** Do not infer behavior from file names. Read the actual owner files.
4. **Check feature flags:** Experimental functionality must be default-off (`#[cfg(feature = "...")]`).
5. **Check constraints:** Never block the SDL thread, preserve single state owner, no new services unless justified.

### When writing code

1. **Smallest testable unit:** Implement one independently testable change at a time.
2. **Run negative tests before claiming success:** Test invalid inputs, missing services, duplicate requests.
3. **Reuse existing dependencies:** Prefer existing crates and patterns over new ones.
4. **Preserve existing capabilities:** Do not rewrite working code just because a new architecture is available.
5. **Document as you go:** Update `docs/` for any user-facing or architectural change.

### Before submitting

1. **Run checks:** `cargo fmt --check`, `cargo clippy -D warnings`, `cargo test`
2. **Update docs:** If the change affects users or architecture, update `docs/`
3. **Add changeset:** For code/behavior changes
4. **Open draft PR:** Against `arena/*` branch (session-tracked) or feature branch

### Never do

- Do not claim unexecuted tests as PASS
- Do not fake hardware measurements
- Do not modify physical TV, firmware, root services, or system settings
- Do not force-push or reset other agents' work
- Do not merge PRs automatically
- Do not create independent subsystems when existing owners can be reused

## Pull request template

```markdown
## Summary

Brief description of the change.

## What changed

- File 1: what and why
- File 2: what and why

## Feature flag

- [ ] New feature is default-off
- [ ] All new code is `#[cfg(feature = "...")]` gated
- [ ] Default builds are unchanged

## Tests

- [ ] Unit tests added
- [ ] Negative tests included
- [ ] `cargo test` passes (locally or in CI)

## Documentation

- [ ] `docs/` updated if user-facing or architectural
- [ ] Changeset added (for code/behavior changes)

## Verification

- [ ] Native build result (or BLOCKED with reason)
- [ ] Rollback instructions documented
```

## Review criteria

| Criterion    | Question                                                      |
| ------------ | ------------------------------------------------------------- |
| Reuse        | Does this reuse an existing owner before creating new code?   |
| Single owner | Does `src/state.rs` remain the single state/navigation owner? |
| Non-blocking | Does any blocking work run on the SDL thread?                 |
| Feature flag | Is experimental functionality default-off?                    |
| Fail closed  | Does the integration fail safely when the service is absent?  |
| Tests        | Are there positive and negative tests?                        |
| Docs         | Is documentation updated?                                     |
| Rollback     | Can the change be cleanly reverted?                           |
