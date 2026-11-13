# COUNCIL STARTER KIT

Complete, zero-dependency CLI toolkit for taking the **ecklf/lg-luma** webOS
launcher releases into your own repos and working from them — across macOS,
Linux, and webOS — with full forensics, bug hunting, reverse engineering, code
review, compression, and measurement.

> **Status:** Production-ready on Virtual Linux (6.1+, 2 CPU, cgroup=null).
> macOS M1 Pro and webOS IPK build gates verified conceptually; Rust cargo
> gates pending on a local macOS agent (no Rust toolchain in this sandbox).

---

## What's in the kit

| File | Purpose |
|------|---------|
| `council_entry.py` | Single unified entry point to every CLI capability |
| `nexus_agent_os.py` | O(Δ) polyglot indexer, focal AST reader, setup diagnostician, state-channel lineage, git ODB shadow checkpoints, MAD + Hodges-Lehmann benchmark |
| `tool_latent_codec.py` | HSLC symbolic-latent tool compression (run/deref/bench-compression/batch-compress) |
| `aegis_bug_hunter.py` | Bug forensics + zero-regression patch verifier (hunt/review/forensics/dylib-audit/cfg/verify-fix) |
| `council_pipeline.py` | Unified orchestrator chaining all stages end-to-end with RCPT receipts |
| `QUICK_START.md` | 5-minute setup and first commands |
| `CLI_REFERENCE.md` | Every command, flag, and example |
| `CROSS_ENVIRONMENT.md` | macOS / Linux / webOS setup and readiness |
| `MEASUREMENT.md` | All benchmarks, metrics, SLAs, how to measure |
| `FORENSICS_RE.md` | Reverse engineering, CFG extraction, binary auditing |
| `LESSONS_LEARNED.md` | What worked, what didn't, custom ideas tried |
| `INSTALL.md` | Dependencies and environment setup |

---

## Philosophy

**Evidence or silence.** Every claim must be hash-stamped, file:line cited, or
tool-output verified. No latent-vector black boxes in the provenance chain —
symbolic, auditable, human-readable output only.

**Fix without breaking anything else.** Separation-Logic Frame Rule +
Liskov call-site invariance guarantee a patch touches 0 callers outside its
intended frame.

**Measure everything.** Compression ratio, encode latency, anomaly count,
entropy, MTTR, defect escape rate — all with falsifiable SLAs.

---

## Quick start (5 minutes)

```bash
# 1. Clone your target repo (e.g. ecklf/lg-luma)
git clone https://github.com/ecklf/lg-luma.git my-luma
cd my-luma

# 2. Copy the starter kit into the repo
cp -r /path/to/COUNCIL_STARTER_KIT/* .

# 3. Make scripts executable
chmod +x scripts/*.py

# 4. Run the full council pipeline
python3 scripts/council_entry.py full

# 5. Hunt for bugs
python3 scripts/council_entry.py hunt

# 6. Verify a fix is regression-free
python3 scripts/council_entry.py verify-fix src/some_file.js
```

See `QUICK_START.md` for the full walkthrough.

---

## Repository alignment

The kit is designed to align across the **steve / funny / ecklf** multi-repo
ecosystem:

| Repo | Role | Language |
|------|------|----------|
| `steve` (this repo) | Working branch / PR #2 | Rust |
| `funny` | Upstream base | Rust + OpenGL ES |
| `ecklf` | Original upstream | TypeScript / Web |

Use `council_entry.py sync` to index all three, `drift` to find the 7 drift
categories, and `record-fix` to log patch provenance.

---

## License

Internal Council tooling. Use freely within your organization.