# CROSS-ENVIRONMENT READINESS — macOS / Linux / webOS

The Council CLIs are designed to run identically on **Virtual Linux (6.1+)**,
**macOS M1 Pro**, and **webOS** targets. This document details setup for each.

---

## 1. Virtual Linux (Arena sandbox) — PRIMARY

**Status:** Fully verified. All subcommands exit 0 with RCPT receipts.

```bash
# No setup required — pure Python 3.11 stdlib
python3 --version  # 3.11+

# Run
python3 scripts/council_entry.py full
```

**Verified on:** Arena Linux 6.1.158+, 2 vCPU, cgroup=null (no GPU, no root).

---

## 2. macOS M1 Pro — PLANNED

**Status:** Conceptually verified; no Mac available in this sandbox for
runtime validation. The tools are pure Python and will run unchanged on M1 Pro.

### Setup

```bash
# Python 3.11+ (via python.org or pyenv)
python3 --version

# Optional binutils for reverse engineering (via Homebrew)
brew install binutils  # nm, objdump, strings, readelf
# ldd is not available on macOS; otool -L is used instead
which otool
```

### M1 Pro specific considerations

| Concern | Handling in kit |
|---------|-----------------|
| **Architecture** | `dylib-audit` detects `arm64 (Apple Silicon Native)` vs `x86_64` Mach-O slices and flags `arch_mismatch_hazard` |
| **Rosetta-2** | Labs/macos_m1_pro.md includes Rosetta-2 guard documentation |
| **KV-cache** | `tool_latent_codec` uses KV-prefix canonical ordering for mlx-lm / llama.cpp prefix stability |
| **Memory** | Unified memory — interval arithmetic proofs apply directly |

### Running on M1 Pro

```bash
cd my-luma
python3 scripts/council_entry.py full --workers 4
```

The `--workers` flag defaults to 4; adjust to your core count (M1 Pro: 6-10 cores).

---

## 3. webOS — ISOLATED TEST TARGET

**Critical constraint:** Never modify, launch, or replace production
`space.nuvio.webos`. Use isolated test target `space.nuvio.lab` only.

### webOS lab contract

| Rule | Enforcement |
|------|-------------|
| Production app ID | `space.nuvio.webos` — **never touched** |
| Test app ID | `space.nuvio.lab` — `nuvio_lab` feature + `lab=true` only |
| Silent override | Invalid app IDs fail validation; no silent override |
| Rollback | Requires zero production Nuvio application modification |
| Duplicate routing | No extra media launcher or duplicate routing layer |
| Build metadata | Test target visible in build metadata and receipts |
| Artifact separation | Test artifacts not confusable with production release artifacts |

### IPK build (pending cargo)

```bash
# On a machine with the Rust toolchain:
cargo check --features nuvio,nuvio_lab    # 0 errors required
cargo test --all-features                  # must pass
cargo clippy --all-targets --all-features -- -D warnings  # clean
cargo fmt --all --check                    # clean

# Then build IPK with nuvio_lab feature, app id space.nuvio.lab
```

**Blocked on:** Local macOS agent with cargo/Rust (not available in this
sandbox). See `RESEARCH_RUST_TOOLCHAIN_APPROACHES.md` in the parent repo.

---

## 4. Environment capability matrix

| Capability | Linux | macOS M1 Pro | webOS |
|------------|-------|--------------|-------|
| `sync` (polyglot index) | ✅ Verified | ✅ (Python) | ✅ (Python) |
| `read` (focal reader) | ✅ Verified | ✅ | ✅ |
| `diagnose-setup` | ✅ Verified | ✅ | ✅ |
| `state-lineage` | ✅ Verified | ✅ | ✅ |
| `checkpoint` (git ODB) | ✅ Verified | ✅ | ✅ |
| `bench` (MAD + HL) | ✅ Verified | ✅ | ✅ |
| `hunt` (bug detection) | ✅ Verified | ✅ | ✅ |
| `review` (entropy review) | ✅ Verified | ✅ | ✅ |
| `forensics` (SZZ) | ✅ Verified | ✅ | ✅ |
| `dylib-audit` (binary audit) | ✅ (nm/ldd) | ✅ (nm/otool) | ⚠️ (limited binutils) |
| `cfg` (control-flow graph) | ✅ (objdump) | ✅ (objdump) | ⚠️ (limited objdump) |
| `verify-fix` (frame rule) | ✅ Verified | ✅ | ✅ |
| `run` (latent compression) | ✅ Verified | ✅ | ✅ |
| `deref` | ✅ Verified | ✅ | ✅ |
| `bench-compression` | ✅ Verified | ✅ | ✅ |
| `council pipeline` | ✅ Verified | ✅ | ✅ |
| Rust cargo gates | ❌ Pending | ❌ Pending | ❌ Pending |
| webOS IPK build | ❌ Pending | ❌ Pending | ❌ Pending |

---

## 5. Porting checklist (new repo)

When bringing the kit into a new repo:

```bash
# 1. Copy kit files
cp -r COUNCIL_STARTER_KIT/* /path/to/new-repo/

# 2. Verify Python
python3 --version  # need 3.11+

# 3. Check binutils (optional)
which nm objdump readelf strings ldd otool

# 4. Run smoke test
python3 scripts/council_entry.py sync --path .
python3 scripts/council_entry.py hunt --path .

# 5. Run full pipeline
python3 scripts/council_entry.py full

# 6. If Rust webOS target:
cargo check --features nuvio,nuvio_lab   # requires cargo
```

---

## 6. Known limitations

- **No Rust toolchain in sandbox:** Cargo gates (`cargo check`, `cargo test`,
  `cargo clippy`, `cargo fmt`) cannot be executed here. Must be run on a local
  macOS agent with Rust installed.
- **webOS IPK build:** Requires the webOS SDK and cargo; not available in this
  sandbox.
- **macOS M1 Pro runtime:** Not validated on actual hardware. Pure Python code
  should run unchanged, but binutils availability differs (otool vs ldd).
- **ckgroup=null:** On Linux containers without cgroup v2, telemetry reports
  `null` honestly (no invented values).