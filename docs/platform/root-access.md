# Root Access

## Overview

Root features are only available on rooted TVs (Homebrew Channel with elevated access). Without root, the Root features section is hidden and Luma never attempts system changes.

## Root capabilities

| Capability         | Implementation                                          | Source            |
| ------------------ | ------------------------------------------------------- | ----------------- |
| Boot autostart     | Wake script at `/var/lib/webosbrew/init.d/71-luma-wake` | `src/platform.rs` |
| Home Auto Launch   | `luna://com.webos.settingsservice/setSystemSettings`    | `src/platform.rs` |
| Pad watch          | Gamepad watcher (Start+Select ×2)                       | `src/platform.rs` |
| Elevated inventory | Homebrew `exec` service as root                         | `src/platform.rs` |
| HDMI signal        | `getHDMISignalInfo` as root first                       | `src/platform.rs` |

## Wake script

```
Path: /var/lib/webosbrew/init.d/71-luma-wake
Disable marker: /var/lib/webosbrew/luma-autostart-disabled
```

## Pad watch

```
PID file: /tmp/luma-wake.pid
Binary: /media/developer/apps/usr/palm/applications/com.denisefremov.luma/luma
```

Restarted when the Luma binary is updated (binary newer than PID file).

## Authorization boundary

**Never alter without separate authorization:**

- LG Home or boot behavior
- Firmware
- Root services
- DNS / network filtering
- HDMI / CEC
- HomeKit / AirPlay
- DRM or streaming protection
- System Settings
- Persistent configuration on physical TV

Before any device deployment, require an independent restoration route that does not depend on Luma or LAN access. No device installation is authorized by this documentation.
