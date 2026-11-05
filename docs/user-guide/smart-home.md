# Smart Home (Home Assistant)

## Overview

Luma pairs with Home Assistant via QR code. Your token never has to be typed on the TV. Features: status chips (climate, alarm, lights, doors), scenes, live cameras, device tiles you can toggle with the remote, and per-device hide/show.

## Pairing flow

```
[Settings › Smart Home › Connect]
        |
        v
[QR code displayed on TV]
        |
        v
[User scans with phone → Home Assistant URL + token]
        |
        v
[WebSocket connection established]
        |
        v
[Entities discovered and listed]
```

**Source owners:** `src/smart_home_pairing.rs`, `src/smart_home_ws.rs`, `src/phone_link.rs`

## Entities

| Domain                | Behavior                 |
| --------------------- | ------------------------ |
| `light`               | turn_on / turn_off       |
| `cover`               | open_cover / close_cover |
| `climate`             | Status chip              |
| `alarm_control_panel` | Status chip              |
| `switch`              | turn_on / turn_off       |
| `camera`              | Live camera view         |

## Camera flow

```
[Camera tile → OK]
        |
        v
[Full-screen camera view]
        |
        v
[Wait up to 8s for first picture → offline if none]
```

**Source owner:** `src/smart_home.rs`

## Settings

| Setting           | Description                         |
| ----------------- | ----------------------------------- |
| Show tab          | Toggle Smart Home tab visibility    |
| Selected entities | Entities shown on Home              |
| Selected cameras  | Cameras shown                       |
| Selected scenes   | Scenes shown                        |
| Hidden cameras    | Blurred-only tiles                  |
| Selection version | Empty selection means "recommended" |

**Source owner:** `src/smart_home_settings_view.rs`

## Visual reference

| Screenshot                                 | Shows                       |
| ------------------------------------------ | --------------------------- |
| `docs/screenshots/smart-home.jpg`          | Smart Home tab with cameras |
| `docs/screenshots/settings-smart-home.jpg` | Home Assistant settings     |
