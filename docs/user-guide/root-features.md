# Root Features

## Overview

Luma runs as a normal app without root. On a rooted TV (Homebrew Channel with elevated access), **Settings › System › Root features** appears with additional capabilities.

## Feature matrix

| Feature                                               | Without root | With root       |
| ----------------------------------------------------- | ------------ | --------------- |
| Open Luma when TV turns on (boot / Quick Start+ wake) | —            | ✓               |
| Turn LG Home "Auto Launch" off from Luma              | —            | ✓               |
| Leave Moonlight stream (Start+Select pressed twice)   | —            | ✓               |
| Full app and HDMI input list, app icons               | basic        | ✓ more reliable |
| Detect whether HDMI input has a signal                | —            | ✓               |

Without root, the Root features section is hidden. Luma never tries to change system files without root.

## Implementation

```
root_features(change: Option<RootSet>)        [src/platform.rs]
```

| RootSet                  | Action                              |
| ------------------------ | ----------------------------------- |
| `Wake(true)`             | Write wake script, enable autostart |
| `Wake(false)`            | Touch disable marker, stop watcher  |
| `HomeAutoLaunch(on/off)` | luna-send setSystemSettings         |

**Source owner:** `src/platform.rs`

## Wake script

Path: `/var/lib/webosbrew/init.d/71-luma-wake`  
Disable marker: `/var/lib/webosbrew/luma-autostart-disabled`

## Pad watch

Gamepad watcher for double Start+Select during a stream. Restarted when Luma binary is updated.

PID file: `/tmp/luma-wake.pid`  
Binary: `/media/developer/apps/usr/palm/applications/com.denisefremov.luma/luma`

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
