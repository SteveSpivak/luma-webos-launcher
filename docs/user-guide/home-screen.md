# Home Screen

## Layout (1920×1080 logical)

```
┌─────────────────────────────────────────────────────────────┐
│  Header: clock | date | settings | HDMI inputs              │
├─────────────────────────────────────────────────────────────┤
│  Headline: weather comment + greeting                       │
├─────────────────────────────────────────────────────────────┤
│  Widgets row (right of headline)                            │
├─────────────────────────────────────────────────────────────┤
│  Favorites strip (horizontal, never wraps)                  │
├─────────────────────────────────────────────────────────────┤
│  Stacks rows (2:3 posters, 6 per row + peek)                │
│  └─ Each row: title · source | cards... | View Library     │
└─────────────────────────────────────────────────────────────┘
  Video wallpaper (background, behind all UI)
```

## Components

| Element         | Source owner                                 | Description                                       |
| --------------- | -------------------------------------------- | ------------------------------------------------- |
| Wallpaper       | `src/hw_wallpaper.rs`, `src/aerial_video.rs` | Live video or static background                   |
| Header          | `src/view.rs`                                | Clock, date, settings circle, HDMI input circles  |
| Headline        | `src/view.rs`                                | Weather comment + greeting ("Good evening, Ana.") |
| Widgets         | `src/widgets.rs`, `src/widgets_view.rs`      | Weather, crypto, HDMI, HA status                  |
| Favorites strip | `src/state.rs`, `src/view.rs`                | Horizontal app tiles, never wraps                 |
| Stacks rows     | `src/stacks_view.rs`, `src/stacks.rs`        | Content rows from linked sources                  |
| Focus ring      | `src/view.rs`                                | Animated focus indicator with sheen               |

## Stacks

A stack is a row of content from a linked source. Each stack has:

| Field        | Type      | Description                                   |
| ------------ | --------- | --------------------------------------------- |
| `name`       | String    | Display title                                 |
| `source`     | String    | `"moonlight"`, `"jellyfin"`, `"plex"`         |
| `collection` | String    | Content collection ID                         |
| `shape`      | CardShape | `Poster` (2:3), `Square` (1:1), `Wide` (16:9) |
| `show`       | bool      | Whether row is visible on Home                |

**Max cards per row:** 20 (`HOME_ROW_MAX`).  
**View Library card:** Added at end of row when `has_library(source)` is true (moonlight, jellyfin, plex).

**Source labels:** Moonlight, Jellyfin, Plex.

## Focus on stacks

- Left/Right: move within row
- Up/Down: move between rows
- `stack_scroll: (row, offset, goal)` tracks horizontal scroll per row
- Focus on a card lifts Home until card fully visible
- Leaving a stack row slides it back to first card

## Visual reference

| Screenshot                           | Shows                        |
| ------------------------------------ | ---------------------------- |
| `docs/screenshots/home.jpg`          | Default Home                 |
| `docs/screenshots/home-2.jpg`        | Home with widgets            |
| `docs/screenshots/home-3.jpg`        | Home, morning mist wallpaper |
| `docs/screenshots/home-jellyfin.jpg` | Jellyfin rows on Home        |
