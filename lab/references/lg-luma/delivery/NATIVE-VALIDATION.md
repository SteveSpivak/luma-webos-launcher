# Native desktop validation runbook (prepared, NOT_RUN)

**Accepted audit HEAD / remote branch:** `921d92fb26e4defe0f5e5c3a1b114f2151822908` on `arena/0bee657b-lg-luma`. Remote was absent, then pushed only to that dedicated branch and verified at the same SHA. No main push, merge, TV deployment, Home hook change or video integration is authorized.

**Current preflight:** `native-validation-status.json` — **BLOCKED**, exit **1**. No dependencies were installed and no native test was run.

## Exact missing required tools/inputs

`SDL2-development (pkg-config sdl2)`, `Xvfb`, `cargo`, `clippy-driver`, `cmake`, `node_modules (pnpm install --frozen-lockfile)`, `pkg-config`, `pnpm`, `python3-fontTools`, `rustc`, `rustfmt`, `sdl2-config`, `woff2_decompress`, `xauth`, `xvfb-run`.

Missing optional/reference helpers: `nix`, `rustup`. Available host tools: Node `v22.22.3` (not the Node 24 reference), Python `3.11.2`, Git `2.39.5`. Generated assets and `target/debug/luma` are absent.

## Manual reproducible setup (do not automate from this agent)

Preferred locked reference from `BUILD-ENVIRONMENT.md` / `build-environment.json`:

```sh
# Install/enter Nix by an approved manual method if absent; flake inputs are pinned.
nix develop
pnpm install --frozen-lockfile
pnpm assets
cargo build --locked --package luma --no-default-features
```

CI-equivalent Ubuntu 24.04 manual path, if not using Nix:

```sh
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  libsdl2-dev pkg-config woff2 python3-fonttools libgl1-mesa-dri xvfb xauth cmake
# Provide Node 24 and pnpm 10.34.5 by the approved CI-equivalent method, e.g. corepack:
corepack enable
corepack prepare pnpm@10.34.5 --activate
# Provide Rust 1.93.0 with rustfmt/clippy by the approved CI-equivalent method, e.g. rustup:
rustup toolchain install 1.93.0 --component rustfmt --component clippy
rustup default 1.93.0
pnpm install --frozen-lockfile
pnpm assets
cargo build --locked --package luma --no-default-features
```

Do not substitute npm, regenerate locks, use host SDL for TV, or run `pnpm deploy`. Record actual resolved versions before performance comparison.

## Gate 0 — preflight must become READY

```sh
python3 -B research/scripts/native_preflight.py
```

Expected when ready: exit **0**. Until then, all native gates below remain **BLOCKED**.

## Gate 1 — original native baseline (current dedicated branch, no focus patch)

Run from `/home/user/lg-luma`, with raw receipts outside the checkout:

```sh
E=/home/user/luma-research-evidence/20261102
python3 research/scripts/receipt.py --out "$E" --label native-format -- pnpm format:check
python3 research/scripts/receipt.py --out "$E" --label native-check -- pnpm check
python3 research/scripts/receipt.py --out "$E" --label native-test -- pnpm test
python3 research/scripts/receipt.py --out "$E" --label native-assets -- pnpm assets
python3 research/scripts/receipt.py --out "$E" --label native-desktop-build -- cargo build --locked --package luma --no-default-features
LIBGL_ALWAYS_SOFTWARE=1 LUMA_SMOKE_SKIP_BUILD=1 \
  python3 research/scripts/receipt.py --out "$E" --label native-smoke -- \
  xvfb-run -a -s '-screen 0 1920x1080x24' pnpm test:smoke
```

`pnpm test` includes Cargo workspace tests. A Node subset is not a full baseline PASS.

## Gate 2 — isolated focus-depth worktree

Use a detached validation worktree; do not create or switch another branch:

```sh
git worktree add --detach ../luma-focus-validation 921d92fb26e4defe0f5e5c3a1b114f2151822908
cd ../luma-focus-validation
pnpm install --frozen-lockfile
pnpm assets
cargo build --locked --package luma --no-default-features
git apply --check delivery/patches/focus-depth.patch
git apply delivery/patches/focus-depth.patch
```

The patch is already source-integrity verified; this worktree is for native compilation/behavior only. Do not commit the applied experiment unless separately requested.

## Gate 3 — OFF versus ON rendering and interaction

In the isolated worktree, after a successful build:

```sh
mkdir -p .build/validation
env -u LUMA_FOCUS_DEPTH LIBGL_ALWAYS_SOFTWARE=1 \
  xvfb-run -a -s '-screen 0 1920x1080x24' ./target/debug/luma \
  --assets .build/assets --preferences .build/validation/off.json \
  --profile-frames 240 --script right,right,left,left,apps,home \
  --diagnostics .build/validation/off-render.json --screenshot .build/validation/off.png

env LUMA_FOCUS_DEPTH=1 LIBGL_ALWAYS_SOFTWARE=1 \
  xvfb-run -a -s '-screen 0 1920x1080x24' ./target/debug/luma \
  --assets .build/assets --preferences .build/validation/on.json \
  --profile-frames 240 --script right,right,left,left,apps,home \
  --diagnostics .build/validation/on-render.json --screenshot .build/validation/on.png

LIBGL_ALWAYS_SOFTWARE=1 LUMA_SMOKE_SKIP_BUILD=1 \
  xvfb-run -a -s '-screen 0 1920x1080x24' pnpm test:smoke
cargo test --locked --workspace --all-features focus_experiment
```

Acceptance: OFF preserves baseline draw parameters; ON changes only focused shadow depth; controls/hit rects, navigation, Back and pointer stability remain unchanged. Visual differences must be reported from actual screenshots/diagnostics, not inferred. Current visual difference result: **NOT_RUN**.

## Gate 4 — frame pacing only with working instrumentation

Only if `--profile-frames` produced a nonempty presentation timeline:

```sh
python3 -B research/scripts/analyze_native_diagnostics.py \
  .build/validation/off-render.json .build/validation/off-analysis.json --evidence-class MEASURED_DESKTOP
python3 -B research/scripts/analyze_native_diagnostics.py \
  .build/validation/on-render.json .build/validation/on-analysis.json --evidence-class MEASURED_DESKTOP
```

This reports CPU-side presentation-call cadence and nearest-rank p95/p99. It is **not** GPU time, photon latency, input-to-visible latency or TV performance. If the timeline is missing/empty, result remains UNKNOWN; do not substitute idle loop counts.

## Gate 5 — apply/reverse rollback and native regressions

In the isolated worktree:

```sh
git apply --reverse --check delivery/patches/focus-depth.patch
git apply --reverse delivery/patches/focus-depth.patch
git diff --exit-code -- src
cargo test --locked --workspace --all-features
pnpm test
```

Then, from the main checkout, remove the detached validation worktree only after confirming no unexpected tracked changes or commits:

```sh
git -C ../luma-focus-validation status --porcelain
git worktree remove --force ../luma-focus-validation
```

## Out of scope

Physical-TV deployment, native Home identity/hooks, TV configuration, firmware/DNS/services, real-video integration, protected media, dependency auto-installation, main-branch pushes and merges.
