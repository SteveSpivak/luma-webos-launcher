# Native Home Integration

## Overview

`tv/home.sh` and `tv/home.cjs` provide a root-only, explicit integration for webOS 10/25 and 11/26. They stage a native manifest with ID `com.webos.app.home` and bind-mount it over `/usr/palm/applications/com.webos.app.home`.

## Scripts

| Script                     | Purpose                                                                            |
| -------------------------- | ---------------------------------------------------------------------------------- |
| `tv/home.sh`               | Shell entry point for enable/disable/restore/apply                                 |
| `tv/home.cjs`              | Node script for mount operations                                                   |
| `/etc/init.d/64-luma-home` | TV-side boot hook that reapplies the mount (not a repo file)                       |
| `/etc/init.d/65-luma`      | TV-side cold-boot hook (disable before enabling Home integration; not a repo file) |

## Enable flow

```
[User runs enable]
        |
        v
[y/n confirmation required]
        |
        v
[Create state directory, acquire lock]
        |
        v
[Stage native manifest, symlink executable/libraries/assets]
        |
        v
[Bind-mount over LG Home]
        |
        v
[SAM rereads app via blockSystemApp + releaseBlockSystemApp]
        |
        v
[Verify manifest before stopping previous Home]
```

## Disable / Restore

```
[Remove mount]
        |
        v
[Refresh LG manifest]
        |
        v
[Stop native Home instance]
        |
        v
[Remove boot hook]
```

**Restore scripts remain** in `/var/lib/luma-home` even if the package is removed.

## Luma behavior with Home mount

- Luma's normal tile launch redirects to Home instance
- SDL surface ID set to `com.webos.app.home` when mounted
- Executable stays at installed path for LS2 authentication, `$ORIGIN/lib`, asset discovery, preferences

## Verification required (manual, on TV)

- Home, Back out of last app
- Standby wake with Quick Start+
- Full cold boot
- Saved preferences
- Restoring LG Home

**Build and script checks cannot establish native Home compatibility.**

## Authorization boundary

This integration does **not** change Home Auto Launch or Quick Start+ settings, does not install a remote-key filter, does not create a browser wrapper, and does not change the package's app ID. No further system modifications without separate authorization.
