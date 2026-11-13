#!/usr/bin/env bash
# scripts/ram_workspace.sh — Zero-I/O RAM scratchpad bootstrapper (Council of Experts)
#
# Virtual Linux: /dev/shm (tmpfs, in every container, never touches SSD)
# macOS M1 Pro   : APFS RAM Volume mounted via hdiutil/diskutil (200 GB/s Unified Memory,
#                  lazy allocation, zero SSD wear) + optional APFS clonefile(2) (cp -c)
#
# Usage:
#   source scripts/ram_workspace.sh          # exports ARENA_RAM_DIR
#   scripts/ram_workspace.sh --clean         # unmounts the macOS RAM volume on exit
set -euo pipefail

OS_NAME="$(uname -s)"
VOL_NAME="ArenaRAM"
MOUNT_PATH="/Volumes/${VOL_NAME}"
SIZE_SECTORS=$((2048 * 2048))  # 2048 MiB RAM disk = 4194304 x 512-byte sectors

if [ "$OS_NAME" = "Linux" ]; then
    export ARENA_RAM_DIR="/dev/shm/arena_workspace"
    mkdir -p "$ARENA_RAM_DIR"
    echo "✅ [LINUX RAM DISK] tmpfs scratchpad at: $ARENA_RAM_DIR"

elif [ "$OS_NAME" = "Darwin" ]; then
    if [ ! -d "$MOUNT_PATH" ]; then
        DEV_NODE="$(hdiutil attach -nomount "ram://${SIZE_SECTORS}" | awk '{print $1}')"
        diskutil erasevolume APFS "$VOL_NAME" "$DEV_NODE" >/dev/null 2>&1 || true
    fi
    export ARENA_RAM_DIR="${MOUNT_PATH}/workspace"
    mkdir -p "$ARENA_RAM_DIR"
    echo "✅ [M1 PRO APFS RAM DISK] Unified-memory APFS volume at: $ARENA_RAM_DIR"
    echo "💡 [TIP] Use 'cp -cR <src> <dst>' for instant zero-byte APFS Copy-on-Write clones!"
else
    export ARENA_RAM_DIR="${TMPDIR:-/tmp}/arena_workspace"
    mkdir -p "$ARENA_RAM_DIR"
    echo "⚠️  [UNKNOWN OS] Falling back to TMPDIR scratchpad at: $ARENA_RAM_DIR"
fi

export TMPDIR="$ARENA_RAM_DIR"
export TEMP="$ARENA_RAM_DIR"
export HYPER_RAM_SCRATCH="$ARENA_RAM_DIR"

if [ "${1:-}" = "--clean" ]; then
    trap 'hdiutil detach "$MOUNT_PATH" -force >/dev/null 2>&1 || true' EXIT
    echo "🧹 [CLEANUP] Registered RAM-disk unmount on shell exit."
fi
