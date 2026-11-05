# webOS TV Integration

## App identity

| Property     | Value                               |
| ------------ | ----------------------------------- |
| App ID       | `com.denisefremov.luma`             |
| Home ID      | `com.webos.app.home`                |
| Player ID    | `com.denisefremov.luma.player`      |
| Nivío app ID | `space.nuvio.webos` (feature-gated) |

## Launch integration

Luma launches other apps via Luna service bus:

```
luna://com.webos.applicationManager/launch {"id": <app-id>, "params": <optional>}
```

**Supported launch targets:**

- `com.webos.app.home` — LG Home (redirect when Home mount active)
- `com.webos.app.livetv` — Live TV
- `com.webos.app.browser` — Web Browser
- `com.limelight.webos` — Moonlight game stream
- `com.denisefremov.luma.player` — Luma's own HTML5 player
- `space.nuvio.webos` — Nivío title launch (feature-gated)

**Source owner:** `src/platform.rs`

## Inventory

Luma reads the installed app list via Luna:

```
luna://com.webos.applicationManager/listApps
luna://com.webos.service.eim/getAllInputStatus
```

Apps are filtered: system apps hidden, Luma itself excluded, HDMI inputs mapped, visibility respected.

**Source owner:** `src/platform.rs::normalize_apps()`

## HDMI signals

```
luna://com.webos.service.eim/getHDMISignalInfo
```

Root-first fallback: elevated Homebrew `exec` service, then Luma's own call.

**Source owner:** `src/platform.rs::hdmi_signals()`

## Root features (root only)

| Feature          | Command                                              |
| ---------------- | ---------------------------------------------------- |
| Wake at boot     | Write `/var/lib/webosbrew/init.d/71-luma-wake`       |
| Home Auto Launch | `luna://com.webos.settingsservice/setSystemSettings` |
| Pad watch        | Gamepad watcher (Start+Select ×2)                    |

**Source owner:** `src/platform.rs::root_features()`

## Luna service bus

- **Registration:** Anonymous (avoids SDL collision)
- **Context:** Private GLib context on platform worker
- **Timeout:** 6.5 seconds per call
- **Reply limit:** 2 MiB
- **Impersonation:** `luna-send-pub -a` rejected on webOS 26, not used
- **Elevated service:** Homebrew Channel `org.webosbrew.hbchannel.service/exec` for root-only operations

**Source owner:** `src/luna.rs`

## 4K on TV

Experimental native surface request (`--resolution 4k`). Not guaranteed panel output. Verified on LG C5: forced 4K compositor caused flickering lines and corruption. Default 1080p is stable.

**Source owner:** `src/main.rs`, `development.md`
