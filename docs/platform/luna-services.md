# Luna Service Bus

## Overview

Luma communicates with webOS system services via the Luna service bus (LS2). All calls run on a dedicated platform worker thread with a private GLib context — never on the SDL/UI thread.

## Connection

```rust
// Anonymous registration (avoids SDL collision)
LSRegister(null, &handle, &error)
LSGmainContextAttach(handle, context, &error)
```

**Source owner:** `src/luna.rs::Connection::open()`

## Call pattern

```rust
LSCallOneReply(handle, uri, payload, callback, userdata, &token, &error)
```

- 6.5-second timeout with cancellation
- 2 MiB reply limit
- `checked_response()` validates `returnValue == true`
- Errors truncated to 240 chars, logged with URI context

## Calls made by Luma

| URI | Purpose | Owner |
|---|---|---|
| `com.webos.applicationManager/launch` | Launch an app | `src/platform.rs` |
| `com.webos.applicationManager/listApps` | App inventory | `src/platform.rs` |
| `com.webos.applicationManager/getAppInfo` | App info preflight | `src/platform.rs` |
| `com.webos.service.applicationmanager/closeByAppId` | Close an app | `src/platform.rs` |
| `com.webos.service.eim/getAllInputStatus` | Input device status | `src/platform.rs` |
| `com.webos.service.eim/getHDMISignalInfo` | HDMI signal detection | `src/platform.rs` |
| `com.webos.settingsservice/setSystemSettings` | System settings (root) | `src/platform.rs` |
| `com.webos.settingsservice/getSystemSettings` | Read system settings (root) | `src/platform.rs` |
| `org.webosbrew.hbchannel.service/exec` | Elevated commands (root) | `src/platform.rs` |

## Elevated commands (root only)

Run via Homebrew Channel `exec` service:
```
luna://org.webosbrew.hbchannel.service/exec {"command": "<shell command>"}
```

Used for:
- Root inventory reads (`luna-send` as root)
- Wake script management
- Home Auto Launch changes
- Pad watch management

**Source owner:** `src/platform.rs::root_inventory_read()`, `root_features()`

## Error handling

| Error | Handling |
|---|---|
| `returnValue != true` | Extract `errorText`, truncate to 240 chars |
| Timeout | Cancel token, return "The TV service timed out" |
| Missing service | Return "Native Luna services are only available in an ARM webOS build" (desktop) |
| App not installed | Classify via `player_not_installed()` / `app_not_installed()` |

**Source owner:** `src/platform.rs::checked_response()`, `call()`
