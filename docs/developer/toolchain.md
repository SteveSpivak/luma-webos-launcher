# Toolchain Setup

## Nix flake

The repository uses a Nix flake (`flake.nix`, `flake.lock`) that pins the complete toolchain:

```nix
# Supplies: Rust 1.93, Node.js 24, pnpm 10.34.5, SDL2, pkg-config,
# woff2, Python/fontTools, CMake, Git, Mesa, Xvfb
```

**Supported hosts:** Apple Silicon macOS, ARM64/x86-64 Linux.

## Manual toolchain

### Rust

```sh
rustup toolchain install 1.93
rustup default 1.93
rustup target add armv7-unknown-linux-gnueabi  # TV builds
rustup component add rustfmt clippy
```

**MSRV:** 1.88 (declared in `Cargo.toml`)

### Node.js and pnpm

```sh
# Node 22+
# pnpm 10 (>=10 <11)
corepack enable
corepack prepare pnpm@10.34.5 --activate
```

### System libraries (Debian/Ubuntu)

```sh
sudo apt-get install -y --no-install-recommends \
  libsdl2-dev pkg-config libgl1-mesa-dri xvfb xauth \
  woff2 python3-fonttools
```

### webOS SDK (TV builds only)

```sh
pnpm sdk
export WEBOS_NDK="$PWD/.build/toolchain/arm-webos-linux-gnueabi_sdk-buildroot"
```

**NDK target:** `armv7-unknown-linux-gnueabi` with Cortex-A9/VFP baseline, NEON disabled.

**SDL-webOS:** Pinned to `release-2.30.12-webos.5` via `tools/webos-runtime.mjs`, with SHA-256 verification. Linked as `libSDL2-2.0.so.0` from `$ORIGIN/lib`.

## Verification

```sh
rustc --version    # rustc 1.93.x
cargo --version    # cargo 1.93.x
node --version     # v22.x
pnpm --version     # 10.34.x
pkg-config --exists sdl2 && echo ok
```
