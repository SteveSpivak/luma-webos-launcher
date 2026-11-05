# Visual Reference — Screenshots to Code

This page maps each screenshot in `docs/screenshots/` to the source code that produces it.

## Home and apps

| Screenshot          | Source                                  | Description                  |
| ------------------- | --------------------------------------- | ---------------------------- |
| `home.jpg`          | `src/view.rs`, `src/state.rs`           | Default Home screen          |
| `home-2.jpg`        | `src/widgets.rs`, `src/state.rs`        | Home with widgets            |
| `home-3.jpg`        | `src/hw_wallpaper.rs`                   | Home, morning mist wallpaper |
| `home-jellyfin.jpg` | `src/stacks_view.rs`, `src/jellyfin.rs` | Jellyfin rows on Home        |
| `apps.jpg`          | `src/view.rs::tile()`                   | All apps grid                |

## Movies, series and music

| Screenshot   | Source                              | Description               |
| ------------ | ----------------------------------- | ------------------------- |
| `movie.jpg`  | `src/movie_view.rs`, `src/movie.rs` | Movie page                |
| `series.jpg` | `src/movie_view.rs`, `src/movie.rs` | Series page with episodes |
| `music.jpg`  | `src/music.rs`                      | Now playing               |
| `album.jpg`  | `src/album_view.rs`, `src/album.rs` | Album                     |

## Games (Moonlight)

| Screenshot   | Source                            | Description     |
| ------------ | --------------------------------- | --------------- |
| `game.jpg`   | `src/game_view.rs`, `src/game.rs` | 007 First Light |
| `game-2.jpg` | `src/game_view.rs`, `src/game.rs` | Cyberpunk 2077  |

## Smart Home

| Screenshot                | Source                            | Description                 |
| ------------------------- | --------------------------------- | --------------------------- |
| `smart-home.jpg`          | `src/smart_home.rs`               | Smart Home tab with cameras |
| `settings-smart-home.jpg` | `src/smart_home_settings_view.rs` | Home Assistant settings     |

## Widgets

| Screenshot    | Source                                          | Description    |
| ------------- | ----------------------------------------------- | -------------- |
| `weather.jpg` | `src/weather-service.rs`, `src/widgets_view.rs` | Weather widget |
| `crypto.jpg`  | `src/widgets.rs`, `src/widgets_view.rs`         | Crypto widget  |

## Settings

| Screenshot                | Source                | Description                      |
| ------------------------- | --------------------- | -------------------------------- |
| `settings-general.jpg`    | `src/state.rs`        | General: language, clock, motion |
| `wallpaper-sources.jpg`   | `src/hw_wallpaper.rs` | Wallpaper sources                |
| `wallpapers.jpg`          | `src/hw_wallpaper.rs` | Pick wallpaper clips             |
| `settings-appearance.jpg` | `src/state.rs`        | Appearance                       |
| `appearance-colors.jpg`   | `src/state.rs`        | Accent colors                    |
| `settings-stacks.jpg`     | `src/stacks.rs`       | Stacks                           |
| `settings-inputs.jpg`     | `src/state.rs`        | HDMI inputs                      |
| `settings-system.jpg`     | `src/platform.rs`     | System and root features         |

## How screenshots are generated

`pnpm screenshots` captures native Home, Apps, General, and Inputs into `docs/`. It builds the desktop executable without the TV feature, uses isolated temporary preferences, sample inventory, and a fixed date/time, and captures actual 1920×1080 OpenGL framebuffers. Weather is unconfigured, so no real weather APIs are contacted.

**Command:**

```sh
pnpm screenshots
# or headless:
xvfb-run -a pnpm screenshots
```

These images document the native design, not TV hardware behavior.
