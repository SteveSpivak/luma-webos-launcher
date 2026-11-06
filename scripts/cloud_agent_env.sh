#!/bin/sh
# scripts/cloud_agent_env.sh — Rootless Linux Cloud Agent Toolchain & Headless GLES2 Bootstrap
# Sources or run this script to discover hidden toolchains, unpack rootless SDL2/GLES2
# headers into /tmp/luma-sysroot, and run headless tests in a restricted cloud sandbox.
set -e

SYSROOT="/tmp/luma-sysroot"
mkdir -p "$SYSROOT"

# 1. Probe all common hidden toolchain paths in Cloud Agent containers
for candidate in \
    "$HOME/.cargo/bin" \
    "/root/.cargo/bin" \
    "/usr/local/cargo/bin" \
    "/opt/rust/bin" \
    "/opt/cargo/bin" \
    "$SYSROOT/cargo/bin"
do
    if [ -d "$candidate" ]; then
        export PATH="$candidate:$PATH"
    fi
done

# 2. If cargo is still missing and network is reachable, install minimal toolchain to /tmp
if ! command -v cargo >/dev/null 2>&1; then
    if command -v curl >/dev/null 2>&1; then
        echo "[cloud-agent] Bootstrapping userspace Rust into $SYSROOT..."
        export CARGO_HOME="$SYSROOT/cargo"
        export RUSTUP_HOME="$SYSROOT/rustup"
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
            sh -s -- -y --default-toolchain stable --profile minimal --component rustfmt,clippy
        export PATH="$CARGO_HOME/bin:$PATH"
    fi
fi

# 3. Rootless .deb extraction helper (installs libsdl2-dev & libgles2-mesa-dev without sudo!)
install_deb_rootless() {
    pkg="$1"
    if command -v apt-get >/dev/null 2>&1 && command -v dpkg-deb >/dev/null 2>&1; then
        cd "$SYSROOT"
        apt-get download "$pkg" 2>/dev/null || true
        for deb in ./*.deb; do
            [ -f "$deb" ] && dpkg-deb -x "$deb" "$SYSROOT" && rm -f "$deb"
        done
        cd - >/dev/null
    fi
}

if [ ! -f "/usr/include/GLES2/gl2.h" ] && [ ! -f "$SYSROOT/usr/include/GLES2/gl2.h" ]; then
    install_deb_rootless "libgles2-mesa-dev"
    install_deb_rootless "libegl1-mesa-dev"
    install_deb_rootless "libsdl2-dev"
fi

# 4. Export rootless sysroot compiler/linker flags
export PKG_CONFIG_PATH="$SYSROOT/usr/lib/x86_64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH"
export LIBRARY_PATH="$SYSROOT/usr/lib/x86_64-linux-gnu:$LIBRARY_PATH"
export LD_LIBRARY_PATH="$SYSROOT/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"
export CPATH="$SYSROOT/usr/include:$SYSROOT/usr/include/x86_64-linux-gnu:$CPATH"

# 5. Configure Headless Software OpenGL ES 2.0 + Offscreen SDL2 for Cloud Testing
export SDL_VIDEODRIVER="dummy"
export SDL_AUDIODRIVER="dummy"
export LIBGL_ALWAYS_SOFTWARE="1"
export GALLIUM_DRIVER="llvmpipe"
export EGL_PLATFORM="surfaceless"

echo "[cloud-agent] Environment ready. Cargo: $(command -v cargo || echo 'offline-mode')"
