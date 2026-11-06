# Research: Running Rust Toolchain Checks in Restricted Linux Environment

## Environment Summary

| Property | Value |
|---|---|
| OS | Debian GNU/Linux 12 (bookworm) |
| Architecture | x86_64 |
| Kernel | 6.1.158+ |
| Root access | No (dpkg lock denied) |
| Rust toolchain | NOT installed (cargo/rustc/rustup: command not found, exit 127) |
| Outbound internet | Restricted to: github.com, codeload.github.com, api.github.com, registry.npmjs.org, pypi.org, files.pythonhosted.org |
| static.rust-lang.org | BLOCKED (no response) |
| sh.rustup.rs | BLOCKED (no response) |
| api.github.com | ACCESSIBLE |

## What Needs to Run (from package.json + .github/workflows/ci.yml)

| Check | Command | Status |
|---|---|---|
| Format check | `cargo fmt --all -- --check` | ❌ Blocked — no cargo |
| Clippy lint | `cargo clippy --locked --workspace --all-targets --all-features -- -D warnings` | ❌ Blocked — no cargo |
| Unit tests | `cargo test --locked --workspace --all-features` | ❌ Blocked — no cargo |
| CI toolchain | Rust 1.93.0 (via `dtolnay/rust-toolchain@1.93.0`) | ❌ Blocked locally |

CI also targets `armv7-unknown-linux-gnueabi` (webOS cross-compilation).

---

## Approach 1: GitHub Actions CI (DOCUMENTED PATH — RECOMMENDED)

### Why this is the correct approach

The repository's CI is defined in `.github/workflows/ci.yml` and runs on `ubuntu-24.04` via GitHub Actions. It uses:

```yaml
- uses: dtolnay/rust-toolchain@1.93.0
  with:
    components: rustfmt, clippy
    targets: armv7-unknown-linux-gnueabi
```

This is the canonical, project-sanctioned way to validate Rust code. The `dtolnay/rust-toolchain` action:
- Installs the exact pinned toolchain version (1.93.0)
- Installs requested components (rustfmt, clippy)
- Handles cross-compilation targets
- Is maintained by the Rust ecosystem's most trusted CI automation author (dtolnay)

### What CI will measure

| Check | What it validates | Pass criterion |
|---|---|---|
| `cargo fmt --all -- --check` | Code formatting consistency | No formatting diffs |
| `cargo clippy --locked --workspace --all-targets --all-features -- -D warnings` | Idiomatic Rust, correctness, suspicious code, all lints as errors | Zero clippy warnings across all targets and features |
| `cargo test --locked --workspace --all-features` | Unit tests, integration tests, doc tests | All tests pass |
| Cross-build (`armv7-unknown-linux-gnueabi`) | webOS native binary compilation | Successful cross-build |

### Best practices from research

1. **Pin exact toolchain versions** — Never use `stable` or `latest` in CI; use `1.93.0` as specified in the existing workflow (from [Khimananda 2026 CI/CD guide](https://khimananda.com/blog/ci-cd-pipeline-for-rust-with-github-actions) and [RantAI 2026 guide](https://www.rantai.dev/blog/ci-cd-for-rust-automating-quality-with-github-actions-and-cargo)).

2. **Use `rust-toolchain.toml` for local/CI parity** — A `rust-toolchain.toml` in the project root declares the toolchain version and components, ensuring `dtolnay/rust-toolchain` respects it and developers match CI.

3. **Cache cargo registry and target** — Use `Swatinem/rust-cache@v2` or `actions/cache@v4` to cache `~/.cargo/registry`, `~/.cargo/git`, and `target/` (from [Rust FAQ CI guide](https://www.rustfaq.org/en/how-to-set-up-cicd-for-rust-projects-github-actions/)).

4. **Disable incremental compilation in CI** — `CARGO_INCREMENTAL=0` saves disk and speeds up clean builds (from [Rust FAQ CI guide](https://www.rustfaq.org/en/how-to-set-up-cicd-for-rust-projects-github-actions/)).

5. **Run clippy with `-D warnings`** — Treats all clippy lints as errors, enforcing code quality (from [RantAI 2026 guide](https://www.rantai.dev/blog/ci-cd-for-rust-automating-quality-with-github-actions-and-cargo/)).

6. **Test all feature combinations** — `cargo test --all-features` catches compilation errors hidden behind feature flags (from [Rust FAQ CI guide](https://www.rustfaq.org/en/how-to-set-up-cicd-for-rust-projects-github-actions/)).

7. **Layered static analysis** — Clippy for linting + cargo-audit for dependency vulnerabilities + cargo-deny for license policy (from [IN-COM Data Systems 2026 guide](https://www.in-com.com/blog/the-rust-developers-toolbox-best-static-code-analysis-tools/)).

### Minimal CI workflow template

```yaml
name: Rust CI
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  rust-checks:
    runs-on: ubuntu-24.04
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@1.93.0
        with:
          components: rustfmt, clippy
      - uses: Swatinem/rust-cache@v2
      - name: Format check
        run: cargo fmt --all -- --check
      - name: Clippy (warnings as errors)
        run: cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
      - name: Run tests
        run: cargo test --locked --workspace --all-features
```

---

## Approach 2: Local Rust Toolchain Installation (BLOCKED in this sandbox)

### Method 2a: rustup (standard, requires internet to static.rust-lang.org)

```bash
# Standard online install — BLOCKED: sh.rustup.rs not reachable
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
```

**Blocked:** `sh.rustup.rs` returns no response (firewall blocks non-allowed hosts).

### Method 2b: Standalone tarball from static.rust-lang.org

```bash
# Download and install standalone toolchain — BLOCKED: static.rust-lang.org not reachable
RUST_VERSION=1.93.0
ARCH=x86_64-unknown-linux-gnu
curl -LO "https://static.rust-lang.org/dist/rust-${RUST_VERSION}-${ARCH}.tar.gz"
tar xf "rust-${RUST_VERSION}-${ARCH}.tar.gz"
./rust-${RUST_VERSION}-${ARCH}/install.sh --prefix=$HOME/rust-1.93.0
export PATH="$HOME/rust-1.93.0/bin:$PATH"
```

**Blocked:** `static.rust-lang.org` returns no response.

### Method 2c: apt package manager

```bash
# BLOCKED: no root access (dpkg lock denied)
sudo apt-get install -y rustc cargo
```

**Blocked:** no root privileges.

### Method 2d: Download via GitHub release assets

Checked: `rust-lang/rust` release 1.93.0 has **0 binary assets**. Rust toolchains are not published as GitHub release assets — they are only on `static.rust-lang.org`.

**Blocked:** no assets available via api.github.com.

### Method 2e: rustup-init with --offline (requires pre-downloaded tarball)

```bash
# Requires the toolchain tarball already on disk
./rustup-init --offline --default-toolchain none
rustup toolchain install /path/to/rust-1.93.0-x86_64-unknown-linux-gnu.tar.xz
```

**Blocked:** no way to obtain the tarball locally.

---

## Approach 3: Offline / Vendored Approaches (For Reference)

These approaches are useful in air-gapped or restricted environments but require a machine with internet to pre-stage files:

### 3a: cargo vendor (vendor dependencies locally)

```bash
# On a connected machine:
cargo vendor  # downloads all dependency sources into vendor/
# Then on target:
cargo build --offline --vendored-dir vendor
```

**Limitation:** Vendors crate sources only, not the Rust compiler itself. Still need rustc/cargo binaries.

### 3b: rustup-init --offline with pre-staged toolchain

```bash
# On connected machine: download rustup-init + toolchain tarball
# On target: ./rustup-init --offline --default-toolchain none
# Then: rustup toolchain install /path/to/rust-1.x.x-ARCH.tar.xz
```

**Limitation:** Requires transferring ~100MB+ tarball via sneakernet or internal network.

### 3c: Portable rustup directory transfer

```bash
# On connected machine: install Rust via rustup, then tar up ~/.rustup and ~/.cargo
tar czf rust-portable.tar.gz ~/.rustup ~/.cargo
# On target: extract and add to PATH
```

**Limitation:** Binaries are dynamically linked against host glibc; may not be portable across different Linux distributions.

### 3d: Nix flakes (fully reproducible, but steep learning curve)

```nix
# Pin every dependency including ld-linux.so and glibc
```

**Limitation:** Requires installing Nix; significant complexity.

---

## Approach 4: Python-Based Validation (WHAT WE CAN DO NOW)

Since no Rust toolchain is available locally, we can validate the binary contract using Python:

### What we've already validated (via Python)

| Validation | Method | Result |
|---|---|---|
| FNV-1a-64("continue-watching") | Independent Python computation | `0x01aa2aebbc61d6f6` ✅ |
| FNV-1a-64("watchlist") | Independent Python computation | `0xa05bdde6192df670` ✅ |
| FNV-1a-64("library") | Independent Python computation | `0xe029b3e5014c2890` ✅ |
| LCKV layout (32B header + 396B/card + 8B trailer) | Code inspection of `src/fast_kv.rs` | ✅ |
| MAX_BRIDGE_CARDS=40, MAX_BRIDGE_BYTES=16,384 | Code inspection | ✅ |
| validate_nuvio_target() scheme | Code inspection | `nuvio://tmdb/{movie|tv}/<digits>` ✅ |
| NUVIO_APP_ID="space.nuvio.webos" | Code inspection | ✅ |

### Python validation script template

```python
#!/usr/bin/env python3
"""Validate LCKV binary bridge format using Python (no Rust toolchain required)."""

import struct
import sys

HEADER_SIZE = 32
RECORD_SIZE = 396
TRAILER_SIZE = 8
MAX_BRIDGE_CARDS = 40
MAX_BRIDGE_BYTES = 16_384

def fnv1a_64(data: bytes) -> int:
    h = 0xcbf29ce484222325
    for b in data:
        h ^= b
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h

def validate_lckv(path: str, collection: str) -> list:
    with open(path, "rb") as f:
        buf = f.read()
    
    # Exact size check
    if len(buf) > MAX_BRIDGE_BYTES:
        raise ValueError(f"File exceeds MAX_BRIDGE_BYTES ({MAX_BRIDGE_BYTES})")
    
    if len(buf) < HEADER_SIZE + TRAILER_SIZE:
        raise ValueError("File too short for header + trailer")
    
    # Parse header
    magic = buf[0:4]
    version = buf[4]
    count = struct.unpack_from("<H", buf, 6)[0]
    seq_head = struct.unpack_from("<Q", buf, 8)[0]
    
    # Trailer seq
    tail_offset = len(buf) - TRAILER_SIZE
    seq_tail = struct.unpack_from("<Q", buf, tail_offset)[0]
    
    # Seqlock invariant: head == tail && even
    if seq_head != seq_tail:
        raise ValueError(f"Torn write: head={seq_head} != tail={seq_tail}")
    if seq_head & 1:
        raise ValueError(f"Odd sequence number: {seq_head}")
    
    if count > MAX_BRIDGE_CARDS:
        raise ValueError(f"Card count {count} exceeds MAX_BRIDGE_CARDS={MAX_BRIDGE_CARDS}")
    
    expected_size = HEADER_SIZE + count * RECORD_SIZE + TRAILER_SIZE
    if len(buf) != expected_size:
        raise ValueError(f"Size mismatch: {len(buf)} != {expected_size}")
    
    # Parse records
    cards = []
    offset = HEADER_SIZE
    collection_hash = fnv1a_64(collection.encode())
    
    for i in range(count):
        record = buf[offset:offset + RECORD_SIZE]
        # ... parse fixed-str slots, validate UTF-8, etc.
        cards.append(record)
        offset += RECORD_SIZE
    
    return cards

# Known constants (verified independently)
assert fnv1a_64(b"continue-watching") == 0x01aa2aebbc61d6f6
assert fnv1a_64(b"watchlist") == 0xa05bdde6192df670
assert fnv1a_64(b"library") == 0xe029b3e5014c2890
```

---

## Approach 5: Cross-Compilation from Another Machine

```bash
# On a machine with Rust 1.93.0:
cargo build --release --target armv7-unknown-linux-gnueabi
# Transfer binary to target
scp target/armv7-unknown-linux-gnueabi/release/luma user@target:/
```

**Limitation:** Only validates the compiled binary, not the source-level checks (fmt, clippy, tests). Requires a separate machine with Rust.

---

## Recommended Action Plan

| Step | Action | Owner | Timeline |
|---|---|---|---|
| 1 | Commit source changes to Arena branch (done) | Agent | Complete |
| 2 | Open PR #2 (already open) | Agent | Complete |
| 3 | GitHub Actions CI runs on PR | GitHub | Automatic on push/PR |
| 4 | Review CI results for `cargo fmt`, `cargo clippy`, `cargo test` | Agent + Reviewer | After CI runs |
| 5 | Fix any CI failures, re-push | Agent | As needed |
| 6 | Merge PR after CI green | Reviewer | Per project rules |

### What to monitor in CI

The CI job `build` runs `pnpm check` which executes:
```
cargo clippy --locked --workspace --all-targets --all-features -- -D warnings
```

And `pnpm test` which executes:
```
cargo test --locked --workspace --all-features
```

And `pnpm format:check` which executes:
```
cargo fmt --all -- --check
```

All three must pass for CI to be green. The PR cannot be merged without CI green (per project constraints: "no main merge without CI green").

---

## Forensic Findings from This Investigation

1. **No local Rust toolchain possible** — static.rust-lang.org and sh.rustup.rs are blocked by the sandbox firewall; no root for apt; GitHub releases have no binary assets for rust-lang/rust.

2. **CI is the only validation path** — The project's CI (`.github/workflows/ci.yml`) is designed to run these checks on GitHub's infrastructure with Rust 1.93.0 via `dtolnay/rust-toolchain@1.93.0`.

3. **Python validation supplements but doesn't replace** — We can verify FNV-1a constants and binary layout in Python, but cannot run `cargo test`, `cargo clippy`, or `cargo fmt --check` locally.

4. **Cross-repo parity (TV branch `10f8153`) is BLOCKED** — The branch `10f8153` does not exist in this repository.

---

## References

- [CI/CD for Rust: Automating Quality with GitHub Actions and Cargo](https://www.rantai.dev/blog/ci-cd-for-rust-automating-quality-with-github-actions-and-cargo)
- [How to Set Up CI/CD for Rust Projects (GitHub Actions)](https://www.rustfaq.org/en/how-to-set-up-cicd-for-rust-projects-github-actions/)
- [CI/CD Pipeline for Rust with GitHub Actions: 2026 Guide](https://khimananda.com/blog/ci-cd-pipeline-for-rust-with-github-actions)
- [Rust CI/CD with GitHub Actions: Complete Guide](https://reintech.io/blog/rust-cicd-github-actions-testing-building-deploying)
- [Setting up effective CI/CD for Rust projects](https://www.shuttle.dev/blog/2025/01/23/setup-rust-ci-cd)
- [The Rust Developer's Toolbox: Best Static Code Analysis Tools](https://www.in-com.com/blog/the-rust-developers-toolbox-best-static-code-analysis-tools/)
- [Setting Up and Using Rust Offline](https://buildsoftwaresystems.com/post/rust-offline-development-tutorial/)
- [Installing Rust Offline](https://hatsunearu.github.io/2018/04/29/rust-offline/)
- [r/rust: Rust Offline?](https://www.reddit.com/r/rust/comments/137hmah/rust_offline/)
- Existing repo CI: `.github/workflows/ci.yml`
- Existing package.json scripts: `pnpm check`, `pnpm test`, `pnpm format:check`