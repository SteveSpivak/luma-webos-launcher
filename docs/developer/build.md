# Build from Source

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Rust | 1.88+ (1.93 recommended) | Main language |
| Node | 22+ | Build tooling |
| pnpm | 10 | Package manager |
| SDL2 | — | Desktop preview |
| pkg-config | — | Library detection |
| libgl1-mesa-dri | — | OpenGL (Linux) |
| xvfb | — | Headless CI |
| woff2 | — | Font processing |
| python3-fonttools | — | Font tools |

## With Nix (recommended)

```sh
nix develop
```

The flake supplies Rust 1.93, Cargo/rustfmt/Clippy, Node.js 24, pnpm 10.34.5, SDL2, pkg-config, woff2, Python/fontTools, CMake, and Git.

## Without Nix

```sh
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- --default-toolchain 1.93
rustup target add armv7-unknown-linux-gnueabi  # for TV builds

# Install Node and pnpm
# (use your system package manager or nvm/corepack)

# Install system dependencies (Debian/Ubuntu)
sudo apt-get install libsdl2-dev pkg-config libgl1-mesa-dri xvfb xauth

# Clone and build
pnpm install --frozen-lockfile
pnpm assets
pnpm dev
```

## Desktop preview

```sh
pnpm dev                    # Default 1920×1080
pnpm dev --resolution 4k    # Experimental 4K surface
pnpm dev --script 'home,down' --frames 90  # Scripted navigation
pnpm dev --profile-frames 180  # Frame pacing profile
```

**Headless Linux:**
```sh
xvfb-run -a -s '-screen 0 1920x1080x24' pnpm dev
```

## TV cross-build

```sh
pnpm sdk                    # Download webOS NDK
export WEBOS_NDK="$PWD/.build/toolchain/arm-webos-linux-gnueabi_sdk-buildroot"
pnpm build                  # ARM cross-build
pnpm run package            # IPK + Homebrew feed
```

**TV target:** ARMv7 gnueabi (soft-float), not gnueabihf. NEON disabled for Rust code.

## Commands

| Command | Purpose |
|---|---|
| `pnpm dev [--options]` | Run desktop preview |
| `pnpm assets [--4k]` | Prepare fonts, vector artwork, raster backgrounds |
| `pnpm screenshots` | Capture screenshots into `docs/` |
| `pnpm assets:vector` | Recompile SVG icon/logo meshes |
| `pnpm assets:fonts` | Restore pinned Noto font sources |
| `pnpm sdk` | Download webOS SDK |
| `pnpm runtime` | Prepare SDL-webOS runtime |
| `pnpm build` | Release ARM cross-build |
| `pnpm run package` | Assets, cross-build, IPK, Homebrew feed |
| `pnpm deploy --device tv` | Build/install/launch via ares |
| `pnpm check` | Oxlint and Clippy (no tests) |
| `pnpm format:check` | Formatting check |
| `pnpm test` | Rust unit tests + release tooling |
| `pnpm test:smoke` | Desktop rendering + mocked weather |
| `pnpm changeset` | Add release note |
| `pnpm version:check` | Version synchronization |

## Build artifacts

| Artifact | Location |
|---|---|
| Desktop executable | `target/debug/luma` or `target/release/luma` |
| ARM IPK | `dist/*.ipk` |
| Homebrew feed | `dist/repo.json` |
| Checksums | `dist/sha256sums` |
| Assets | `.build/assets/` |
| SDK | `.build/toolchain/` |
| Rendering diagnostics | `.build/*.png`, `.build/*-render.json` |
