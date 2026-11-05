# Apps Grid

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Category tabs: All | Filter 1 | Filter 2 | ... | Search    │
├─────────────────────────────────────────────────────────────┤
│  App tiles: 6 columns, poster + caption                     │
│  [App] [App] [App] [App] [App] [App]                        │
│  [App] [App] [App] [App] [App] [App]                        │
└─────────────────────────────────────────────────────────────┘
```

## Components

| Element       | Source owner          | Description                            |
| ------------- | --------------------- | -------------------------------------- |
| Category tabs | `src/view.rs`         | Filter tabs (All + source-specific)    |
| App tile      | `src/view.rs::tile()` | Poster, caption, focus ring, zoom      |
| Brand logo    | `src/branding.rs`     | 38 curated brand allowlist             |
| App artwork   | `src/app_artwork.rs`  | Installed app icon discovery and cache |
| Search        | `src/state.rs`        | Query filtering                        |

## App tile details

| Property       | Description                             |
| -------------- | --------------------------------------- |
| Size           | 270×270 (Poster/Square), 566×318 (Wide) |
| Pitch          | 296.4 (Poster/Square), 592.8 (Wide)     |
| Radius         | 26.0                                    |
| Focus zoom     | 1 + 0.07 * pop                          |
| Entrance       | Cascade progress per card on tab entry  |
| Reduced motion | Instant focus, no animation             |

## Artwork resolution

1. Curated vector brand logo (from `branding.rs` allowlist)
2. Installed app icon (from `app_artwork::Service`)
3. Generic category artwork (`assets/surfaces/{brand}.png`)
4. Sampled card color (automatically extracted from artwork)

## Curated brands

38 brands have curated vector logos including: Netflix, YouTube, Apple TV, Disney+, Prime Video, Spotify, Jellyfin, Plex, Kodi, Moonlight, Homebrew Channel, Web Browser, ARTE, ZDF, Das Erste, Coupang Play, Watcha Play, Wavve, Rainbow TV, LG TV VOD, and more.

**Source owner:** `src/branding.rs`

**Note:** Titles and partial ID matches do not select vector overrides. Amazon Alexa retains its own installed icon rather than Prime Video branding.

## Visual reference

| Screenshot                  | Shows         |
| --------------------------- | ------------- |
| `docs/screenshots/apps.jpg` | All apps grid |
