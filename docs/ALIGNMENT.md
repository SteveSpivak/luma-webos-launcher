# Documentation Alignment and Review Process

## Purpose

This document describes how documentation in this repository is written, reviewed, aligned, and refined — so that all agents (human and AI) have full clarity of the project before making additions.

## Documentation model (Diátaxis)

| Category | Purpose | Location | Audience |
|---|---|---|---|
| Tutorial | Learning-oriented, step-by-step | `docs/user-guide/` | New users, contributors |
| How-to guide | Problem-oriented, task-specific | `docs/developer/` | Developers, agents |
| Explanation | Understanding-oriented, concepts | `docs/architecture/`, `docs/platform/` | Architects, agents |
| Reference | Information-oriented, exhaustive | `docs/reference/` | Everyone |

## Writing standards

1. **Source-backed:** Every claim about behavior is traceable to specific source files and functions. No inference from file names.
2. **No speculation:** Runtime behavior on physical TV is documented only where verified. Unknowns are marked BLOCKED.
3. **Single source of truth:** Each concept is documented in one place. Cross-references link to related pages.
4. **Scannable:** Use tables, code blocks, and short paragraphs. Lead with summaries.
5. **Navigable:** Every folder has a README.md index. Every page links to its parent and related pages.

## Review process for documentation

When a code change is proposed, documentation is reviewed alongside it:

| Review question | Pass criteria |
|---|---|
| Does the PR update docs for user-facing changes? | `docs/user-guide/` or `docs/overview.md` updated if behavior changes |
| Does the PR update docs for architectural changes? | `docs/architecture/` updated if components/flows change |
| Does the PR update docs for build/test changes? | `docs/developer/` updated if procedures change |
| Are negative test scenarios documented? | `docs/developer/testing.md` or test comments cover failure modes |
| Is the rollback documented? | Rollback instructions present for reversible changes |
| Is the feature flag documented? | New features are default-off and documented as such |

## Alignment across agents

All agents work on the same branch. Before making documentation changes:

1. Read `docs/README.md` for the documentation index
2. Read `docs/AGENT-GUIDE.md` for how agents should work
3. Check `git log --oneline -5` for recent changes
4. Check `gh pr list --state open` for in-flight work
5. Coordinate on shared files (`docs/README.md`, `docs/architecture/`, `docs/developer/contributing.md`)

## Versioning

Documentation is versioned with the code. When a release is cut:
- `docs/` changes are included in the release PR
- `CHANGELOG.md` documents user-facing doc changes
- Outdated docs are removed or marked as superseded

## What is NOT documentation

- Inline code comments are for local clarity, not a substitute for `docs/`
- Commit messages describe what changed, not how the system works
- Issue/PR discussions are ephemeral; decisions must be recorded in `docs/`
