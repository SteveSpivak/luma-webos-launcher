# Application Lifecycle

## Startup

```
[Process start]
        |
        v
Options::parse()                              [src/main.rs]
        |
        +-- SAM launch metadata (argv[1] on webOS)
        +-- webos_home flag (Home mount integration)
        |
        v
Platform::new(webos)                          [src/platform.rs]
        |
        v
Assets::load(root, webos)                     [src/view.rs]
        |
        v
Preferences load                              [src/storage.rs]
        |
        v
State::new(preferences)                       [src/state.rs]
        |
        v
[First frame draw]
        |
        v
Platform::Refresh → inventory read          [src/platform.rs]
        |
        v
state.set_inventory(inventory, warning)       [src/state.rs]
        |
        v
reconcile_focus() → first_content()
```

**Startup stages** (logged on TV): asset metadata, preferences, inventory, first frame.

**Verified first-frame latency:** ~399 ms on development TV (previous vector-font startup). New rendering paths need hardware comparisons.

## Shutdown

```
[Remote: Back from Home]
        |
        v
state.back() → Effect::Quit                   [src/state.rs]
        |
        v
main.rs effects() → return false              [src/main.rs]
        |
        v
[Run loop exits]
        |
        v
[Workers dropped, connections unregistered]
        |
        v
[Process exits]
```

**Source owner:** `src/main.rs` (run loop), `src/state.rs` (back)

## Foreground / Background

| Event                  | Behavior                                                           |
| ---------------------- | ------------------------------------------------------------------ |
| Window becomes visible | Inventory refresh, artwork reload                                  |
| Window hidden          | Idle behavior, VSync paces animation                               |
| TV standby wake        | Luma may open at boot (root feature: `wake`)                       |
| Home Auto Launch       | LG setting, preserved by Luma (not changed)                        |
| Relaunch               | Normal tile launch redirects to Home instance if Home mount active |

## webOS launch integration

- **SAM launch metadata:** JSON object in `argv[1]`. Contains `@system_native_app` and `nid`.
- **Anonymous LS2 registration:** Avoids collisions with SDL's registration. Hub still applies executable's role.
- **`luna-send-pub -a` impersonation:** Rejected on webOS 26, not used.
- **LS2 calls:** One worker's private GLib context, 6.5-second budget, 2 MiB reply limit.
- **App ID:** `com.denisefremov.luma` (surface identity for SDL and LS2).

## Native Home integration (root-only, optional)

`tv/home.sh` / `tv/home.cjs` stage a native manifest with ID `com.webos.app.home` and bind-mount over LG Home. Scripts:

- `enable` — requires `y`/`n` confirmation, creates state dir, acquires lock, invokes installer
- `disable` / `restore` — removes mount, refreshes manifest, stops Home instance
- `64-luma-home` — boot hook that reapplies mount
- `65-luma` — cold-boot hook (disable before enabling Home integration)

**Never alter:** LG Home, firmware, compositor settings, system hooks, DNS, HDMI/CEC, HomeKit/AirPlay, DRM, System Settings, or persistent config on physical TV without separate authorization.
