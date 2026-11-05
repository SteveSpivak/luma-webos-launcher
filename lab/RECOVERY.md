# LG TV / launcher risk and recovery gates

**No device modification authorized by this kit.** Target app default ID `com.denisefremov.luma` is the **same as upstream advanced launcher**, so attempting to install a changed build may upgrade/replace that app. Before any real-TV experiment, propose a distinct **test app ID**, audit all ID-derived storage paths, companion player IDs (`com.denisefremov.luma.player`), home/autostart/root hooks and Homebrew feed. Demonstrate independent stock Home restoration, launcher uninstall and original app/config reinstatement. Validate application-manager launch permissions and installed Nuvio target.

### Protected invariants
Native HomeKit/AirPlay; TV network control and IP pairing; Magic Remote/D-pad and Back precedence; audio/voice/input/HDMI/CEC; other streaming apps including Nuvio DRM, Settings, software updates, standalone recovery. No egress filter or DNS lockdown change, firmware flash, `/etc/hosts` overlay, bind mounts, system compositor hooks, root scripts or protected media access. Root features default OFF, no auto-home takeover.

### Gates
G0: static source checks + offline contract negative tests.
G1: desktop native tests/screenshots/perf reference, no physical TV.
G2: package identity dependency inventory, app ID isolation, backed up build artifacts, reversible uninstall rehearsal **in simulation**, real rollback still NOT_RUN.
G3: explicit owner approval for a bounded physical install/launch; TV model/firmware recorded; backup+restore independent from launcher+LAN; test only separate candidate app. One title launch into Nuvio details, one manual Back/Home, no playback. Never alter system Home behavior.
G4: optional read-only owner-approved telemetry; wallpaper media plane and other root-only features remain independent future approvals.

### Stop
First unexpected fault in Home/remote/streaming/Settings or unbounded resource growth => stop and attempt only approved rollback. If recovery cannot be proven independently, do not install.
