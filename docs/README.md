# Luma Documentation

Welcome to the Luma documentation. Luma is a fast, remote-first native launcher and home screen for LG webOS TVs, written in Rust and drawn with OpenGL ES 2.

This documentation covers the project **as it exists now**, before any new feature additions. It is written for contributors, maintainers, and AI coding agents who need full clarity of the codebase before making changes.

## How to use this documentation

| If you want to... | Start here |
|---|---|
| Understand what Luma is and what it does | [`overview.md`](overview.md) |
| See the system architecture and component map | [`architecture/system-overview.md`](architecture/system-overview.md) |
| Trace a key user flow (Home → app launch → Back) | [`user-guide/navigation.md`](user-guide/navigation.md) |
| Build, test, or contribute code | [`developer/build.md`](developer/build.md) |
| Understand webOS TV integration | [`platform/webos.md`](platform/webos.md) |
| Look up preferences, app IDs, or terms | [`/reference`](reference/README.md) |
| See how screens map to code | [`user-guide/home-screen.md`](user-guide/home-screen.md) |
| Work with AI coding agents on this repo | [`developer/contributing.md`](developer/contributing.md) |

## Documentation model

This documentation follows the [Diátaxis](https://diataxis.fr/) model:

- **Tutorials** (`user-guide/`) — learning-oriented, step-by-step
- **How-to guides** (`developer/`) — problem-oriented, task-specific
- **Explanation** (`architecture/`, `platform/`) — understanding-oriented, concepts and decisions
- **Reference** (`reference/`) — information-oriented, exhaustive technical descriptions

## Repository layout

```
luma-webos-launcher/
├── Cargo.toml / Cargo.lock       Rust workspace and pinned dependencies
├── src/                          Rust launcher, platform adapter, GLES2 shaders
│   ├── main.rs                   Application entry point and run loop
│   ├── state.rs                  Single owner of UI state, navigation, effects
│   ├── view.rs                   Rendering scene construction and controls
│   ├── platform.rs               TV platform worker and Luna service calls
│   ├── stacks.rs                 Home stack source registry
│   ├── stacks_view.rs            Stack card rendering
│   ├── jellyfin.rs / plex.rs / moonlight.rs   Media and game source integrations
│   ├── smart_home.rs             Home Assistant integration
│   ├── widgets.rs                Home widgets (weather, crypto, HDMI, HA status)
│   ├── media.rs                  Shared media types and artwork download
│   ├── app_artwork.rs            Installed app artwork discovery and cache
│   ├── renderer.rs               OpenGL ES 2 rendering thread
│   ├── motion.rs                 Focus animation and transitions
│   ├── model.rs                  Data models (App, Input, Preferences, Inventory)
│   ├── storage.rs                Preferences persistence
│   ├── i18n.rs                   Translations (en/de/es/zh/pt)
│   ├── tests.rs                  Unit tests
│   └── ... (48 source modules)
├── assets/                       SVGs, fonts, wallpapers, translations, artwork metadata
├── vector-geometry/              Shared fill tessellation and vector boundary coverage
├── tools/                        Asset prep, SDK setup, packaging, release feed
├── tests/                        Desktop rendering and mocked HTTP smoke scripts
├── tv/                           Optional root-only native Home integration scripts
├── native/                       webOS-specific C helpers and player
├── docs/                         This documentation
├── development.md                Detailed development reference (build, CI, releases)
└── README.md                     Project front door (features, install, tech stack)
```

## What exists vs. what is planned

| Area | Status |
|---|---|
| Core launcher (Home, Apps, Settings, navigation) | Implemented |
| Jellyfin / Plex media browsing | Implemented |
| Moonlight game streaming | Implemented |
| Smart Home (Home Assistant) | Implemented |
| Widgets (weather, crypto, HDMI, HA status) | Implemented |
| Video wallpapers | Implemented |
| Nuvio title-to-detail launch (Phase 1) | Implemented, default-off feature flag |
| Nuvio Continue Watching stack row (Phase 2) | Blocked — needs Nuvio producer API contract |
| Nuvio Home row (Phase 3) | Blocked — depends on Phase 2 |

## Nivío integration (feature-scoped docs)

The following documents cover the Nivío title-to-detail launch integration specifically. They are **integration-scoped** (feature-specific), not whole-project documentation:

| Doc | Purpose |
|---|---|
| [`CHARTER.md`](CHARTER.md) | Nivío project charter, scope, authorization boundaries |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Nivío architecture and component map |
| [`INTEGRATION-AUDIT.md`](INTEGRATION-AUDIT.md) | Nivío integration audit against existing code |
| [`REUSE-MATRIX.md`](REUSE-MATRIX.md) | What Nivío reuses vs. what it must create |
| [`USER-STORIES.md`](USER-STORIES.md) | Nivío user stories and acceptance criteria |
| [`USER-FLOWS.md`](USER-FLOWS.md) | Nivío user flows and sequence diagrams |
| [`COMPONENTS.md`](COMPONENTS.md) | Nivío component definitions |
| [`MEASUREMENT.md`](MEASUREMENT.md) | Nivío metrics and observability |
| [`RISKS-ROLLBACK.md`](RISKS-ROLLBACK.md) | Nivío risks and rollback procedure |
| [`NEXT-STEP.md`](NEXT-STEP.md) | Nivío next-step plan and blockers |

These docs describe work on a separate feature branch (`research/arena-nuvio-integration-kit-20261105`) and are not part of the core Luma documentation set.

## Active pull requests

| PR | Branch | Purpose | Status |
|---|---|---|---|
| [#1](https://github.com/SteveSpivak/luma-webos-launcher/pull/1) | `research/arena-nuvio-integration-kit-20261105` | Lab: Nivio integration kit preparation (research, audit, charter) | Open, draft |
| [#2](https://github.com/SteveSpivak/luma-webos-launcher/pull/2) | `arena/5fe14abb-luma-webos-launcher` | Implementation: Nivio Phase 1 launch + whole-project documentation | Open, draft |

PR #1 is the prepared lab branch with integration-scoped documentation. PR #2 is the current working branch containing the Nivío Phase 1 implementation (default-off feature flag) and the whole-project documentation set. Both target `main` and must be reviewed before merge.

## Contributing

See [`developer/contributing.md`](developer/contributing.md) for how to work on this codebase, run tests, and submit changes. All changes must be committed to a feature branch and submitted as a draft pull request — never merged automatically.
