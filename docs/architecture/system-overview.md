# System Overview

## Runtime architecture

Luma is a single-process native application with a clear separation between the UI/render thread and background workers.

```
┌─────────────────────────────────────────────────────────────┐
│                     SDL Event Loop (UI thread)              │
│  Remote input → state.direction()/activate()/back() →       │
│  effects → Platform requests → Response handling → redraw   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     State (single owner)                    │
│  page, focus, stack_items, launching, movie_cache,          │
│  preferences, playback_progress, widgets, weather, etc.     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────┐          ┌──────────┐          ┌──────────┐
│ Platform │          │ Jellyfin │          │  Moonlight │
│ worker   │          │ worker   │          │  worker  │
│ (Luna)   │          │ (HTTP)   │          │ (TCP/UDP)│
└──────────┘          └──────────┘          └──────────┘
        │                     │                     │
        ▼                     ▼                     ▼
   TV services         Jellyfin server     Sunshine/Apollo
   (LS2 bus)           (Quick Connect)     PC game stream
```

## Thread model

| Thread | Responsibility |
|---|---|
| SDL/UI thread | Event loop, rendering, state mutations |
| Platform worker | Blocking Luna service calls (never on UI thread) |
| Jellyfin worker | HTTP requests to Jellyfin server |
| Plex worker | HTTP requests to Plex server |
| Moonlight worker | TCP/UDP discovery, pairing, game stream |
| Artwork worker | Image decode and upload |
| Weather worker | Forecast fetching with generation IDs |
| Thumb service | Episode still downloading |
| Smart Home WS | Home Assistant WebSocket connection |

## Feature gating

| Feature | Cargo feature | Default |
|---|---|---|
| TV platform (Luna, arm only) | `webos` | Off (desktop builds) |
| Nivío title launch | `nuvio` | Off |
| Video wallpaper | Compile-time constant `VIDEO_WALLPAPER_SUPPORTED = true` | gated by runtime verification |

## Key design principles

1. **Never block the SDL/rendering thread** — all blocking work (Luna calls, HTTP, image decode) runs on dedicated workers.
2. **Single navigation and state owner** — `src/state.rs` owns all state, focus, and effects. No duplicated state machines.
3. **Platform calls originate from the native executable** — not from a CLI process impersonating app identity.
4. **No new services or dependencies** — reuse existing workers and patterns before adding new ones.
5. **Experimental functionality default OFF** — `nuvio` feature is off by default.
6. **Fail closed** — optional integrations fail without crashing the launcher.

## Process boundaries

- **In-process:** All Rust code runs in a single native executable (`luma`).
- **Out-of-process (TV only):** Jellyfin/Plex/Moonlight media play in separate web apps or PC streams. Luma launches them via Luna service bus.
- **Out-of-process (root only):** Homebrew Channel `exec` service for elevated inventory reads and root feature changes.
