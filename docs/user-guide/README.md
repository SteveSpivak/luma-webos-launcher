# User Guide

This guide describes Luma's user-facing screens and interactions **as they exist now**. It maps screens to source code so contributors and AI agents can understand what each screen does and where it is implemented.

## Contents

- [`home-screen.md`](home-screen.md) — Home screen: favorites, stacks, widgets, wallpaper
- [`navigation.md`](navigation.md) — D-pad, Magic Remote, Back precedence, focus transitions
- [`apps-grid.md`](apps-grid.md) — Apps grid: search, categories, favorites
- [`media.md`](media.md) — Jellyfin/Plex: browsing, detail pages, playback
- [`games.md`](games.md) — Moonlight: game library, play stream
- [`smart-home.md`](smart-home.md) — Home Assistant: entities, scenes, cameras
- [`widgets.md`](widgets.md) — Widgets: weather, crypto, HDMI, HA status
- [`settings.md`](settings.md) — All settings sections
- [`root-features.md`](root-features.md) — Root features (rooted TVs only)
- [`screens.md`](screens.md) — Visual reference: screenshots mapped to code

## Interaction model

- **Built for the D-pad:** Back always steps one level out.
- **Magic Remote pointer:** Works everywhere, including drag-to-scroll.
- **OK/Enter:** Activate on release (not press).
- **Hold OK for 600 ms:** Reorder Home favorite or open app options.
- **Escape / Back / Backspace:** Parent navigation, overlay dismissal, or quit from Home.
- **Menu / M / right-click:** App options.
- **Pointer / wheel:** Hover, click, hold, and scrolling.
- **F5:** Refresh inventory (desktop).

## Focus model

Focus is a single owner in `src/state.rs`. Focus level is tweened (0 to 1) for animation. Focus pop provides a one-off spring and light sheen. Reduced-motion users get instant focus (no animation).

## Back precedence

Back is handled by `state.back()` with this order:
1. Ambient mode → leave ambient
2. Moving selection → cancel move
3. Game shot → clear shot
4. Game active → close game
5. Album active → close album
6. Playback active → close playback (saves progress)
7. Movie active → close movie (saves progress)
8. Overlay → dismiss overlay
9. Settings subpage → close subpage
10. Settings section → pop section
11. Page → previous page
12. Home → quit application
