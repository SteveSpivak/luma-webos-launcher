# INSTALL — Dependencies and environment setup

---

## Required

| Dependency | Version | Why |
|------------|---------|-----|
| Python | 3.11+ | All CLIs are pure Python 3.11 stdlib |

Check:
```bash
python3 --version
```

---

## Optional (for reverse engineering depth)

| Tool | Purpose | Install |
|------|---------|---------|
| `nm` | Symbol tables | `sudo apt install binutils` (Linux) / `brew install binutils` (macOS) |
| `objdump` | Disassembly / CFG | Same as above |
| `readelf` | ELF dependency sections | Same as above |
| `strings` | Printable string extraction | Same as above |
| `ldd` | Shared library deps (Linux) | `sudo apt install libc-bin` (Linux) |
| `otool` | Mach-O deps (macOS) | Xcode Command Line Tools |

The CLIs detect which tools are available and degrade gracefully. Without
binutils, `dylib-audit` and `cfg` still work via raw header parsing but with
less detail.

---

## Install in a new repo

```bash
# 1. Copy the starter kit
cp -r /path/to/COUNCIL_STARTER_KIT/* /path/to/your-repo/
cd /path/to/your-repo

# 2. Make scripts executable
chmod +x scripts/*.py

# 3. Verify Python
python3 --version

# 4. Check optional binutils
which nm objdump readelf strings ldd otool  # optional

# 5. Smoke test
python3 scripts/council_entry.py sync --path .

# 6. Full pipeline
python3 scripts/council_entry.py full --workers 4
```

---

## No pip install required

All scripts import only from the Python 3.11 standard library:
`ast`, `collections`, `concurrent.futures`, `datetime`, `hashlib`, `json`,
`math`, `os`, `platform`, `re`, `resource`, `shutil`, `sqlite3`, `struct`,
`subprocess`, `sys`, `time`, `zlib`, `pathlib`, `argparse`.

No `hypothesis`, `pint`, `mutmut`, or other third-party packages are needed
for the CLIs themselves. (Those were used in separate quality-assurance labs
in the parent repo.)

---

## webOS IPK build (requires additional tooling)

```bash
# Rust toolchain (for space.nuvio.lab feature)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# webOS SDK (LG)
# Download from LG developer site

# Then:
cargo check --features nuvio,nuvio_lab
cargo test --all-features
cargo clippy --all-targets --all-features -- -D warnings
cargo fmt --all --check
```

**Blocked in this sandbox** — requires a local macOS agent with cargo and the
webOS SDK.