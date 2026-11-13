# Architecture

This section explains how Luma is built: the system overview, component map, data flows, and lifecycle. All observations are traced from actual source code in `src/`, not inferred from file names.

## Contents

- [`system-overview.md`](system-overview.md) — High-level system design and runtime architecture
- [`component-map.md`](component-map.md) — Every component, its source files, responsibilities, and dependencies
- [`data-flows.md`](data-flows.md) — Key end-to-end data flows traced through source
- [`lifecycle.md`](lifecycle.md) — Application lifecycle: startup, shutdown, resume, foreground/background

## Documentation principles

- **Source-backed:** Every claim is traceable to specific files and functions.
- **No speculation:** Runtime behavior on physical TV is documented only where verified.
- **Single owner:** Each component has one identified owner file. No duplicated ownership.
- **Feature-gated:** Experimental functionality (e.g. Nuvio launch) is behind `#[cfg(feature = "nuvio")]` and off by default.
