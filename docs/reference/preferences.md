# Preferences Reference

## Overview

Preferences are stored as JSON in a local file on the TV. They are loaded at startup, sanitized, and saved atomically (temp-file rename).

**Source owner:** `src/model.rs::Preferences`, `src/storage.rs`

## Storage locations

| Platform        | Path                                             |
| --------------- | ------------------------------------------------ |
| TV (developer)  | `/media/developer/<appid>/preferences.json`      |
| TV (production) | `/media/internal/.<appid>/preferences.json`      |
| TV (temp)       | `/media/developer/temp/<appid>/preferences.json` |
| Desktop         | `$XDG_CONFIG_HOME/luma-native/preferences.json`  |

## Preferences structure

| Field                 | Type                        | Default     | Description                     |
| --------------------- | --------------------------- | ----------- | ------------------------------- |
| `favorites`           | `Option<Vec<String>>`       | null        | Favorite app IDs                |
| `hidden`              | `Vec<String>`               | []          | Hidden app IDs                  |
| `background`          | String                      | "dunes"     | Wallpaper background ID         |
| `video_index`         | usize                       | 0           | Selected wallpaper video        |
| `video_sources_mask`  | u8                          | ALL_SOURCES | Video source bitmask            |
| `video_excluded`      | BTreeSet<String>            | []          | Excluded videos                 |
| `video_shuffle`       | bool                        | true        | Shuffle wallpaper videos        |
| `show_home_names`     | bool                        | false       | Show app names on Home          |
| `show_app_names`      | bool                        | true        | Show app names on Apps          |
| `hour_24`             | bool                        | false       | 24-hour clock                   |
| `reduced_motion`      | bool                        | false       | Disable animations              |
| `show_seconds`        | bool                        | false       | Show seconds in clock           |
| `greeting_name`       | String                      | ""          | Name for greeting               |
| `heading_font`        | HeadingFont                 | Nunito      | Heading font                    |
| `text_font`           | TextFont                    | Manrope     | Text font                       |
| `heading_size_pct`    | u8                          | 130         | Heading size (85–170)           |
| `text_size_pct`       | u8                          | 90          | Text size (90–150)              |
| `ui_sounds`           | bool                        | true        | UI sound effects                |
| `screensaver_minutes` | u8                          | 10          | Screensaver timeout (0 = never) |
| `ui_resolution`       | UiResolution                | Qhd         | UI density                      |
| `auto_ui_cap`         | UiResolution                | Uhd         | Auto resolution ceiling         |
| `greeting_style`      | GreetingStyle               | Rude        | Greeting style                  |
| `input_modes`         | BTreeMap<String, InputMode> | {}          | HDMI input modes                |
| `input_names`         | BTreeMap<String, String>    | {}          | Custom input names              |
| `show_weather`        | bool                        | true        | Show weather                    |
| `weather_location`    | Option<Location>            | null        | Weather city                    |
| `temperature_unit`    | Unit                        | Celsius     | Temperature unit                |
| `language`            | Language                    | En          | UI language                     |
| `smart_home`          | SmartHomePreferences        | default     | Home Assistant config           |
| `accent`              | Accent                      | default     | Accent color/gradient           |
| `stacks`              | Vec<StackConfig>            | []          | Home stack rows                 |
| `moonlight`           | MoonlightLink               | default     | Moonlight connection            |
| `jellyfin`            | JellyfinLink                | default     | Jellyfin connection             |
| `plex`                | PlexLink                    | default     | Plex connection                 |
| `games`               | GameLibrary                 | default     | Game history/favorites          |
| `playback_progress`   | BTreeMap<String, u64>       | {}          | Media playback positions        |
| `luma_player`         | bool                        | true        | Use Luma player                 |
| `widgets`             | WidgetPrefs                 | default     | Widget preferences              |

## Sanitization

`preferences.sanitize()` is called on load to:

- Clamp sizes to valid ranges
- Remove unsupported stack sources (keep only moonlight/jellyfin/plex)
- Validate video exclusions against catalog
- Reset invalid background to "dunes"
- Clean and truncate ID lists (max 1000)
- Validate input modes and names (max 128 names, 40 chars each)

**Source owner:** `src/model.rs::Preferences::sanitize()`

## Input modes

| Mode   | Description                                                    |
| ------ | -------------------------------------------------------------- |
| `Auto` | Shown while device sends picture; fallback to cable plugged in |
| `On`   | Always shown                                                   |
| `Off`  | Never shown                                                    |

## Card shapes

| Shape  | Aspect | Size    | Pitch | Use                   |
| ------ | ------ | ------- | ----- | --------------------- |
| Poster | 2:3    | 270×405 | 296.4 | Movies, series, games |
| Square | 1:1    | 270×270 | 296.4 | Music                 |
| Wide   | 16:9   | 566×318 | 592.8 | Videos                |

**Source owner:** `src/stacks.rs::CardShape`

## UI resolutions

| Resolution  | Logical size                      |
| ----------- | --------------------------------- |
| Auto        | Follows auto_ui_cap (default Uhd) |
| 4k (Uhd)    | 3840×2160                         |
| 1440p (Qhd) | 2560×1440                         |
| 1080p (Hd)  | 1920×1080                         |

**Source owner:** `src/model.rs::UiResolution`

## Languages

| Code | Name               |
| ---- | ------------------ |
| en   | English            |
| de   | Deutsch            |
| es   | Español            |
| zh   | 简体中文           |
| pt   | Português (Brasil) |

**Source owner:** `src/i18n.rs::Language`
