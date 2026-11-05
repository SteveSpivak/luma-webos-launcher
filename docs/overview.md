# Project Overview

## What Luma is

Luma is a fast, remote-first native launcher and home screen for LG webOS TVs. It replaces the cluttered LG Home with one calm screen: favorite apps, live video wallpapers, widgets, Jellyfin/Plex media libraries, Moonlight PC game streaming, and Home Assistant smart home devices.

Luma is a native Rust application drawn with OpenGL ES 2. It runs as a normal app on webOS without root. On rooted TVs (Homebrew Channel with elevated access), additional root features become available.

**App ID:** `com.denisefremov.luma`  
**Version:** 2.2.160  
**License:** MIT  
**Maintainer:** Denis Efremov (denisefremov.com)

## Core capabilities

| Capability | Description | Source owner |
|---|---|---|
| Home screen | Favorite apps strip, stacks (content rows), widgets, wallpaper, headline, clock, date | `src/state.rs`, `src/view.rs`, `src/stacks_view.rs` |
| Apps grid | All installed apps, search, categories, favorites toggle | `src/view.rs`, `src/state.rs` |
| Stacks | Rows of content from linked sources (Jellyfin, Plex, Moonlight) with "View Library" | `src/stacks.rs`, `src/stacks_view.rs` |
| Video wallpapers | Live aerials and video collections, hardware playback | `src/aerial_video.rs`, `src/hw_wallpaper.rs` |
| Widgets | Weather, crypto, HDMI input preview, Home Assistant status | `src/widgets.rs`, `src/widgets_state.rs`, `src/widgets_view.rs` |
| Jellyfin | Sign in via Quick Connect, browse libraries, play media | `src/jellyfin.rs` |
| Plex | Sign in via plex.tv PIN, browse libraries, play media | `src/plex.rs` |
| Moonlight | Steam games from PC via Sunshine/Apollo, play stream | `src/moonlight.rs` |
| Smart Home | Home Assistant pairing, entities, scenes, cameras | `src/smart_home.rs`, `src/smart_home_ws.rs` |
| Media player | Built-in HTML5 web player for Jellyfin/Plex playback | `src/player.rs`, `native/cinema/` |
| Platform launch | App launch to other TV apps via Luna service bus | `src/platform.rs` |
| Nuvio launch | Launch Nuvio titles by contentTarget (default-off feature) | `src/platform.rs`, `src/state.rs` |

## Tech stack

| Layer | Technology |
|---|---|
| Language | Rust 2024 edition, MSRV 1.88 |
| UI | SDL2, OpenGL ES 2, custom GLSL shaders |
| Text | `owned_ttf_parser`, custom SVG→triangle compiler (lyon tessellation), signed-distance edges |
| Images | `image` crate (PNG, JPEG, WebP), decoded off render thread |
| Networking | `ureq` + `rustls`, `tungstenite` WebSocket (Home Assistant), `mdns-sd` and UDP discovery |
| Moonlight pairing | `rcgen`, `rsa`, `x509-parser`, AES (GameStream / Sunshine protocol) |
| QR codes | `qrcode` |
| Video wallpapers | webOS hardware media pipeline (C helpers in `native/`) |
| Player | Separate web app: HTML5 video, HLS, vanilla JS |
| TV integration | Luna service bus (LS2), Homebrew Channel elevated service |
| Build tooling | pnpm, Node, `sharp`, `@webos-tools/cli`, Nix flake, oxlint / oxfmt, Changesets |

## Privacy

- No telemetry, no accounts, no ads.
- Settings, favorites and tokens stay in a local JSON file on the TV.
- No API keys built in. Sign-ins go through Quick Connect, Plex link codes, or QR code on phone.
- Weather uses user-chosen location, never IP geolocation.

## Supported platforms

- **Target:** LG webOS TVs (ARMv7, gnueabi soft-float calling convention)
- **Verified:** webOS 26 (LG OLED55C57LA C5), external testing confirms webOS 6+
- **Desktop preview:** Linux with SDL2 and OpenGL (xvfb-run for headless CI)
- **4K:** Experimental native surface request; not guaranteed panel output

## Project history

Luma started as a fork of [ecklf/lg-luma](https://github.com/ecklf/lg-luma). Most of the code in this fork was written with AI coding assistants (Claude Code and OpenAI Codex), directed and tested on a real LG OLED C1 by the maintainer. Every change was checked on the TV before release.

## Related links

- [Luma case study](https://denisefremov.com/work/luma.html) — design story
- [webOS Homebrew](https://www.webosbrew.org/)
- [Moonlight](https://moonlight-stream.org/)
- [Sunshine](https://github.com/LizardByte/Sunshine) / [Apollo](https://github.com/ClassicOldSong/Apollo)
- [Jellyfin](https://jellyfin.org/)
- [Home Assistant](https://www.home-assistant.io/)
- [Releases](https://github.com/SteveSpivak/luma-webos-launcher/releases/latest)
