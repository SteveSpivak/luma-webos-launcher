# Settings

## Settings sections

| Section | Description | Source |
|---|---|---|
| General | Language, clock, motion, greeting, app names | `src/state.rs` |
| Wallpaper | Background, video sources, shuffle | `src/state.rs`, `src/hw_wallpaper.rs` |
| Stacks | Content rows from linked sources | `src/stacks.rs`, `src/state.rs` |
| Widgets | Widget types, sizes, positions | `src/widgets.rs` |
| Smart Home | Home Assistant pairing, entities | `src/smart_home.rs` |
| Inputs | HDMI input names and visibility | `src/state.rs` |
| System | Root features (rooted TVs only) | `src/platform.rs` |

## General settings

| Setting | Type | Default |
|---|---|---|
| Language | en / de / es / zh / pt | en |
| Hour 24 | bool | false |
| Show seconds | bool | false |
| Reduced motion | bool | false |
| Screensaver minutes | u8 | 10 |
| UI resolution | Auto / 4K / 1440p / 1080p | Qhd (1440p) |
| Heading font | Nunito / other | Nunito |
| Text font | Manrope / other | Manrope |
| Heading size % | 85–170 | 130 |
| Text size % | 90–150 | 90 |
| UI sounds | bool | true |
| Greeting name | String | "" |
| Greeting style | Rude / Classic | Rude |

## Wallpaper settings

| Setting | Type | Default |
|---|---|---|
| Background | dunes / midnight / prism / ... | dunes |
| Video index | usize | 0 |
| Video sources mask | u8 | ALL_SOURCES |
| Video excluded | BTreeSet<String> | empty |
| Video shuffle | bool | true |

## Stacks settings

| Setting | Type | Default |
|---|---|---|
| Source | moonlight / jellyfin / plex | jellyfin |
| Collection | source-dependent | fresh |
| Shape | Poster / Square / Wide | Poster |
| Show | bool | true |

**Source owner:** `src/stacks.rs`

## Input settings

| Setting | Type |
|---|---|
| Input mode | Auto / On / Off |
| Input name | String (max 40 chars) |

**Source owner:** `src/state.rs`

## Root features (rooted TVs only)

| Feature | Without root | With root |
|---|---|---|
| Open Luma at TV power-on | — | ✓ |
| Turn LG Home Auto Launch off | — | ✓ |
| Moonlight stream exit (Start+Select ×2) | — | ✓ |
| Full app and HDMI input list | basic | ✓ more reliable |
| HDMI signal detection | — | ✓ |

**Source owner:** `src/platform.rs` (root_features)

## Preferences file

- **TV:** App-owned persistent directory (`/media/developer/<appid>/`, `/media/internal/.<appid>/`)
- **Desktop:** `$XDG_CONFIG_HOME/luma-native/preferences.json`
- **Format:** JSON, atomic temp-file rename writes
- **Import:** Existing JSON preferences imported once on startup

**Source owner:** `src/storage.rs`
