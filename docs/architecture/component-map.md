# Component Map

Every component in Luma, its source files, responsibilities, and dependencies. Traced from actual source code.

## Core (always compiled)

| Component | Source files | Responsibility | Depends on |
|---|---|---|---|
| Application entry | `src/main.rs` | Run loop, SDL init, effect dispatch, response handling | platform, state, view, weather, smart_home |
| UI state & navigation | `src/state.rs` | Single owner: page, focus, stack_items, launching, effects, Back precedence | model, motion, renderer, weather, smart_home, widgets |
| Rendering scene | `src/view.rs` | Scene construction, controls, focus rings, zoom, sheen, animations | model, motion, renderer, branding, app_artwork |
| Renderer | `src/renderer.rs` | OpenGL ES 2 rendering thread, draw commands, texture upload, frame pacing | raster, vector, typography, font |
| Data models | `src/model.rs` | App, Input, Inventory, Preferences, valid_app_id, demo_inventory | branding, video_catalog, typography, weather |
| Platform worker | `src/platform.rs` | Luna service calls, app launch, inventory, root features | luna, model |
| Luna FFI | `src/luna.rs` | LS2 bindings (LSCallOneReply, GLib context), 6.5s timeout | libc, glib |
| Storage | `src/storage.rs` | Preferences persistence, atomic temp-file rename | model |
| Translations | `src/i18n.rs` | 5-language message catalog (en/de/es/zh/pt) | assets/messages.json, time |
| Motion | `src/motion.rs` | Focus animation springs, entrance cascades, card rise, sheen | — |
| Typography | `src/typography.rs` | Font loading, heading/text fonts, sizes | owned_ttf_parser |
| Raster | `src/raster.rs` | Size constants (HD, UHD) | — |
| Vector | `src/vector.rs` | Vector geometry types | luma-vector-geometry |
| Diagnostics | `src/diagnostics.rs` | Rendering diagnostics capture | renderer |

## Media integrations

| Component | Source files | Responsibility | Depends on |
|---|---|---|---|
| Shared media | `src/media.rs` | Detail, PlayRequest, Episode, LibraryPage, download_as, poster_backdrop, ThumbService | ureq, image |
| Jellyfin | `src/jellyfin.rs` | Quick Connect sign-in, library fetch, details, play, albums | media, stacks |
| Plex | `src/plex.rs` | plex.tv PIN sign-in, library fetch, details, play | media, stacks |
| Moonlight | `src/moonlight.rs` | Discovery, pairing, game cache, play launch | stacks, rcgen, rsa, rustls, aes |
| Media player | `src/player.rs`, `src/player_backend.rs` | HTML5 web player session, OpenRequest handling | media |
| Player view | `src/player_view.rs` | Player UI (timeline, audio/subtitle/quality chapters) | player |
| Library | `src/library.rs` | Library grid browsing | media, stacks |
| Library view | `src/library_view.rs` | Library rendering | library, view |

## Home features

| Component | Source files | Responsibility | Depends on |
|---|---|---|---|
| Stacks registry | `src/stacks.rs` | StackConfig, StackItem, SOURCES list, has_library, collection_choices | — |
| Stacks view | `src/stacks_view.rs` | Stack card rendering (posters, library card, focus rings) | stacks, view |
| Widgets | `src/widgets.rs` | Widget framework (weather, crypto, HDMI, HA status) | weather, smart_home |
| Widgets state | `src/widgets_state.rs` | Widget state management | widgets |
| Widgets view | `src/widgets_view.rs` | Widget rendering | widgets, view |
| Settings art | `src/settings_art.rs` | Settings page illustrations | view |
| Aerial video | `src/aerial_video.rs`, `src/aerial_video.json` | Video wallpaper clips | hw_wallpaper |
| HW wallpaper | `src/hw_wallpaper.rs` | Native video wallpaper pipeline | — |

## Smart Home

| Component | Source files | Responsibility | Depends on |
|---|---|---|---|
| Smart Home | `src/smart_home.rs` | Home Assistant pairing, entities, scenes, cameras | weather-service |
| Smart Home WS | `src/smart_home_ws.rs` | WebSocket connection to Home Assistant | tungstenite |
| Smart Home pairing | `src/smart_home_pairing.rs` | QR code pairing flow | phone_link, qrcode |
| Smart Home settings view | `src/smart_home_settings_view.rs` | Settings UI for Smart Home | smart_home |
| Phone link | `src/phone_link.rs` | QR matrix, random hex, pairing utilities | qrcode |

## Platform & TV integration

| Component | Source files | Responsibility | Depends on |
|---|---|---|---|
| Platform | `src/platform.rs` | App launch, inventory, root features, HDMI signals, Nivío launch | luna, model |
| App artwork | `src/app_artwork.rs` | Installed app icon discovery, decode, cache | image, model |
| TV compatibility | `src/webos-compat.rs` | getauxval for SDK libc | — |
| Native Home | `tv/home.sh`, `tv/home.cjs` | Root-only native Home mount (webOS 10/25, 11/26) | — |
| Wake script | `tv/luma-wake.sh` | Cold-boot launch hook | — |
| App icon reader | `tv/read-app-icon.cjs` | Homebrew elevated icon reader | Node |

## Supporting

| Component | Source files | Responsibility | Depends on |
|---|---|---|---|
| Branding | `src/branding.rs` | 38 curated brand/logo allowlist | — |
| Video catalog | `src/video_catalog.rs` | Built-in video sources | — |
| Steam | `src/steam.rs` | Steam game lookup | — |
| Music | `src/music.rs` | Music playback session | media |
| Mini | `src/mini.rs` | Mini player | — |
| Mini view | `src/mini_view.rs` | Mini player UI | mini |
| Album | `src/album.rs` | Album card | — |
| Album view | `src/album_view.rs` | Album UI | album |
| Game | `src/game.rs` | Game card | — |
| Game view | `src/game_view.rs` | Game UI | game |
| Movie | `src/movie.rs` | Movie card, open_movie flow | media |
| Movie view | `src/movie_view.rs` | Movie UI | movie |
| Scroll preview | `src/scroll-preview.rs` | Scroll preview placeholder | — |
| Pad watch | `src/pad_watch.rs` | Gamepad watcher (Start+Select double) | — |
| UI sound | `src/ui_sound.rs` | UI sound effects | — |
| Weather | `src/weather.rs` | Weather display logic | weather-service |
| Weather service | `src/weather-service.rs` | Weather fetching, cache, geocoding | ureq, time |
| Weather phrases | `src/weather_phrases.rs` | Weather headline phrases | — |
| Weather sky | `src/weather_sky.rs` | Weather sky backgrounds | — |
| TVOS settings view | `src/tvos_settings_view.rs` | tvOS-style settings UI | — |
| Widgets settings view | `src/widgets_settings_view.rs` | Widget settings UI | widgets |

## Tests

| Component | Source files | Responsibility |
|---|---|---|
| Unit tests | `src/tests.rs` | Navigation, preferences, localization, rendering geometry, weather, Nivío launch |
| App artwork tests | `src/app-artwork-tests.rs` | Artwork decode and cache tests |
| Weather tests | `src/weather-tests.rs` | Weather state tests |

## External tooling

| Tool | Purpose |
|---|---|
| `tools/build-webos.sh` | ARM cross-build script |
| `tools/setup-webos-sdk.mjs` | webOS SDK download |
| `tools/webos-runtime.mjs` | SDL-webOS runtime prep |
| `tools/package.mjs` | IPK packaging and Homebrew feed |
| `tools/assets.mjs` | Asset preparation (fonts, vector, raster) |
| `tools/screenshots.mjs` | Screenshot capture |
| `tools/ipk.mjs` | IPK verification |
| `tools/repository.mjs` | Homebrew feed generation |
| `tools/deploy.mjs` | Device deploy via ares |
| `tools/release-gate.mjs` | Release gating |
| `tools/sync-version.mjs` | Version synchronization |
| `tools/font-catalog.py` | Font catalog generation |
| `tools/font-pairs.py` | Font pair generation |
| `tools/font-weights.py` | Font weight generation |
| `tools/assets.mjs` | Asset build |
| `tools/brand-assets.mjs` | Brand asset prep |
| `tools/weather-sky-assets.mjs` | Weather sky asset prep |
| `tools/vector-assets.mjs` | Vector asset compilation |

## Nivío integration (feature-gated, default off)

| Component | Source files | Responsibility |
|---|---|---|
| Nivío launch | `src/platform.rs` (NuvioLaunch request, validate_nuvio_target, nuvio_launch_params) | Launch Nuvio titles by contentTarget |
| Nivío state | `src/state.rs` (Effect::NuvioLaunch, Target::NuvioLaunch, activate arm) | State and focus handling for Nivío launch |
| Nivío dispatch | `src/main.rs` (effects arm, Response::Launched handling) | Effect dispatch and error notice |
| Nivío translations | `assets/messages.json` (nuvioNotInstalled, 5 locales) | Translated error messages |
| Nivío tests | `src/tests.rs` (mod nuvio, 8 tests) | Validation, payload, routing, duplicate block, focus |
