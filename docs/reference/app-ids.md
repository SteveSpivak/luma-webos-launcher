# Application ID Reference

## Luma app IDs

| ID | Purpose |
|---|---|
| `com.denisefremov.luma` | Luma launcher (main app) |
| `com.denisefremov.luma.player` | Luma's HTML5 web player |
| `com.webos.app.home` | LG Home |
| `space.nuvio.webos` | Nivío app (feature-gated launch target) |

## Excluded from app inventory

These app IDs are excluded from Luma's app grid (normalized away in `normalize_apps()`):

- `com.denisefremov.luma` (Luma itself)
- `com.webos.app.home` (LG Home)
- `com.webos.app.livetv` (Live TV — handled separately as "live")
- `com.webos.app.hdmi*` (HDMI inputs — handled as inputs)
- `com.webos.app.externalinput.*` (external inputs)
- `com.webos.*`, `com.palm.*`, `com.lge.*` (system apps — unless explicitly visible)
- Non-visible apps (unless Live TV)

## Valid app ID format

```
valid_app_id(id): non-empty, ≤128 chars,
dot/underscore/dash-separated alphanumeric parts
```

**Source owner:** `src/model.rs::valid_app_id()`

## Curated brand allowlist

38 brands have curated vector logos in `src/branding.rs`. Examples:

| Brand | App ID pattern |
|---|---|
| Netflix | `netflix` |
| YouTube | `youtube.leanback.v4` |
| Apple TV | `com.apple.appletv` |
| Disney+ | `com.disney.disneyplus-prod` |
| Prime Video | `amazon` |
| Spotify | `spotify-beehive` |
| Jellyfin | `org.jellyfin.webos` |
| Plex | `plex` |
| Kodi | `org.xbmc.kodi` |
| Moonlight | `com.limelight.webos` |
| Homebrew Channel | `org.webosbrew.hbchannel` |
| Web Browser | `com.webos.app.browser` |

**Note:** Titles and partial ID matches do not select vector overrides. Amazon Alexa retains its own installed icon rather than Prime Video branding.

**Source owner:** `src/branding.rs`

## Demo inventory

`demo_inventory()` returns 27+ demo apps for desktop preview, including all curated brands plus Live TV, Web Browser, ARTE, ZDF, Das Erste, Coupang Play, Watcha Play, Wavve, Rainbow TV, LG TV VOD, and OLED Gallery.

**Source owner:** `src/model.rs::demo_inventory()`
