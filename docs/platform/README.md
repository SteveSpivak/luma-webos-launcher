# Platform

This section covers Luma's integration with LG webOS TVs: Luna services, root features, native Home integration, and TV-specific behavior.

## Contents

- [`webos.md`](webos.md) — webOS TV integration overview
- [`luna-services.md`](luna-services.md) — Luna service bus usage
- [`root-access.md`](root-access.md) — Root features (rooted TVs only)
- [`native-home.md`](native-home.md) — Native Home mount integration

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

## Supported firmware

- **Verified:** webOS 26 (LG OLED55C57LA C5)
- **External testing:** webOS 6+
- **NDK target:** ARMv7 gnueabi (soft-float)
- **SDL-webOS:** `release-2.30.12-webos.5`
