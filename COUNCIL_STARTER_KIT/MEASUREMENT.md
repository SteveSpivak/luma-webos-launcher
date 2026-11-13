# MEASUREMENT — Benchmarks, metrics, SLAs, and how to measure

All metrics are falsifiable with stated SLAs. Every benchmark emits JSON and an
RCPT receipt via `arena_guard.py exec`.

---

## 1. Nexus Agent OS performance

| Metric | Result | SLA | How to measure |
|--------|--------|-----|----------------|
| Sync (cold, parallel) | ~380ms | <500ms | `time python3 scripts/nexus_agent_os.py sync` |
| Sync (warm, parallel) | ~70ms | <100ms | Run sync twice; compare |
| Sync (cold, sequential) | ~381ms | N/A | `--workers 1` |
| Parallel speedup (cold) | 1.06x | >1.0x | cold_sequential / cold_parallel |
| Cache speedup (warm) | 5.31x | >2.0x | cold_parallel / warm_parallel |
| Files scanned | 180 | N/A | Output `files_scanned` |
| Functions modeled | 259-4,253 | N/A | Output `functions_modeled` |
| Call sites cross-checked | 3,311-3,665 | N/A | Output `call_sites_cross_checked` |

---

## 2. Tool Latent Codec (HSLC compression)

| Metric | Result | SLA | How to measure |
|--------|--------|-----|----------------|
| Compression ratio | 653.53x | >15x | `bench-compression` output |
| Raw tokens | 356,175 | N/A | Stress test: 5,255 errors / 26,279 lines |
| Compressed tokens | 545 | N/A | Same |
| Coordinate recall | 100% | 100% (zero blur) | Check root-cause coordinates in output |
| Root-cause classes recovered | 4/4 | 4/4 | Same |
| Encode latency | ~298ms | <150ms (normal) / <500ms (stress) | Same |
| Batch compression (2 files) | 10.86x | >5x | `batch-compress` |

**SLAs (from the HSLC scorecard):**
- L1: Token compression ratio 15x–250x (we achieve 653x on stress test)
- L2: Root-cause coordinate recall 100%
- L3: CPU encode latency ≤150ms on normal outputs
- L4: Handle dereference fidelity 100% lossless

---

## 3. Aegis Bug Hunter

| Metric | Result | SLA | How to measure |
|--------|--------|-----|----------------|
| Hunt duration | 124.1ms | <500ms | `time python3 scripts/aegis_bug_hunter.py hunt` |
| Files scanned | 34 | N/A | Output `files_scanned` |
| Functions modeled | 259 | N/A | Output `functions_modeled` |
| Call sites checked | 3,665 | N/A | Output `call_sites_cross_checked` |
| Anomalies found | 4 | N/A | Output `total_anomalies_found` |
| Per-file cost | 3.65ms | <10ms | duration / files |
| CFG extraction | 91.75ms | <500ms | `cfg /bin/true` |
| CFG nodes | 899 | N/A | Output `node_count` |
| CFG edges | 1,400 | N/A | Output `edge_count` |
| Verify-fix | SAFE_TO_SHIP | SAFE_TO_SHIP | `verify-fix <file>` |

**Bug-hunting SLAs (B1–B5):**
- B1: Liskov caller preservation — 0% broken callers
- B2: AST-SZZ root-cause attribution — 100% traced
- B3: Patch dispersion entropy — ≤2.2 bits
- B4: Deviance anomaly delta — ≤0 (monotonically decreasing)
- B5: Bug-twin eradication rate — 100%

---

## 4. Council Pipeline (end-to-end)

| Metric | Result | SLA |
|--------|--------|-----|
| Total duration | 809ms | <2s |
| Stages | 6 | N/A |
| All stages pass | True | True |
| RCPT receipts per stage | 1 | 1 |

---

## 5. How to run the full benchmark suite

```bash
python3 scripts/labs/13_performance_benchmark/benchmark_runner.py
```

**Output:** JSON with all benchmarks, summary line:

```
Nexus cache speedup: 5.31x | Latent codec compression: 653.53x |
Aegis hunt: 124.1ms (34 files) | Council pipeline: 809.02ms
```

---

## 6. Recording metrics

Append to `metrics/ledger.jsonl` after each run:

```jsonl
{"timestamp": "...", "metric": "nexus_cache_speedup_x", "value": 5.31, "run": "council-pass-3"}
{"timestamp": "...", "metric": "latent_codec_compression_x", "value": 653.53, "run": "council-pass-3"}
```

See `docs/MEASUREMENT.md` in the parent repo for the full metrics schema.

---

## 7. SLA enforcement

The `verify-fix` subcommand enforces B1 (Liskov) and B4 (zero new anomalies)
mechanically — it returns exit code 1 if either fails, blocking the ship.