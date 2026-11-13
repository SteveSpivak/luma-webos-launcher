# CLI REFERENCE — Every command, flag, and example

All commands are invoked via the unified entry point:

```bash
python3 scripts/council_entry.py <subcommand> [options]
```

Or directly:

```bash
python3 scripts/<script_name>.py <subcommand> [options]
```

---

## 1. NEXUS AGENT OS — `scripts/nexus_agent_os.py`

### `sync` — O(Δ) wait-free polyglot indexer

```bash
python3 scripts/council_entry.py sync --path . --workers 4
```

| Flag | Default | Description |
|------|---------|-------------|
| `--path` | `.` | Directory to index |
| `--workers` | `4` | Parallel file-parsing workers |

**Output:** JSON with file count, symbol count, channel count, trap count, duration.

**Performance:** Cold ~380ms, warm ~70ms (5.31x cache speedup), 180 files → 4,253 symbols.

---

### `read` — Focal + skeleton AST reader

```bash
# Read a file with all symbols elided except the focal one
python3 scripts/council_entry.py read scripts/arena_guard.py --symbol cmd_audit

# Optional line window
python3 scripts/council_entry.py read scripts/arena_guard.py --lines 1:40
```

**What it does:** Shows every symbol as a 1-line skeleton (elided), and the focal
symbol at 100% fidelity with exact byte offsets. Cuts tokens ~85% vs `cat`.

---

### `diagnose-setup` — Import-time trap diagnostician

```bash
python3 scripts/council_entry.py diagnose-setup --path .
```

**Finds:** 5 root causes of collection errors:
1. Unguarded `os.environ["KEY"]` at import time (KeyError trap)
2. Eager I/O / DB / network at import time
3. Unset environment variables referenced in code
4. Missing `__init__.py` / sys.path roots
5. conftest.py discovery

---

### `state-lineage` — Bipartite state-channel graph

```bash
# Trace all writers and readers of an env var
python3 scripts/council_entry.py state-lineage "ENV:DATABASE_URL"

# Trace class attribute access
python3 scripts/council_entry.py state-lineage "ATTR:"

# Trace SQL table access
python3 scripts/council_entry.py state-lineage "SQL_TABLE:"
```

**Output:** WRITERS_MUTATORS vs READERS_CONSUMERS per channel, grouped.

---

### `checkpoint` — 3ms git ODB shadow tree

```bash
# Save a snapshot before editing
python3 scripts/council_entry.py checkpoint save --label "pre-fix"

# Restore byte-exact state
python3 scripts/council_entry.py checkpoint restore --id SHDW-ABCD1234

# List all checkpoints
python3 scripts/council_entry.py checkpoint list
```

**Latency:** ~15-20ms save/restore, instant undo without touching branches.

---

### `bench` — MAD + Hodges-Lehmann A/B benchmark

```bash
python3 scripts/council_entry.py bench "cmd_a" "cmd_b" --runs 7
```

**Output:** Interleaved A/B execution, median, MAD, Hodges-Lehmann shift,
verdict (`CANDIDATE_FASTER` / `NO_SIGNIFICANT_GAIN_BEYOND_VM_JITTER`).

---

## 2. AEGIS BUG HUNTER — `scripts/aegis_bug_hunter.py`

### `hunt` — Engler deviance mining + PVS-Studio AST anomalies

```bash
python3 scripts/council_entry.py hunt --path .
```

**Detects:**

| Category | Severity | What it means |
|----------|----------|---------------|
| `CALL_ARITY_MISMATCH_TYPEERROR` | CRITICAL | Wrong argument count at call site |
| `UNAWAITED_ASYNC_COROUTINE` | CRITICAL | Async coroutine dropped, never awaited |
| `ENGLER_DEVIANT_IGNORED_RETURN` | MEDIUM | Return value ignored (statistical outlier) |
| `ENGLER_DEVIANT_UNGUARDED_CALL` | MEDIUM | Missing try/except (statistical outlier) |
| `TAUTOLOGICAL_COMPARISON_COPY_PASTE` | HIGH | `x == x` (copy-paste slip) |
| `REDUNDANT_BOOLEAN_SUBEXPRESSION` | HIGH | `a and a` duplicate |
| `DEAD_DUPLICATE_ELIF_BRANCH` | HIGH | Duplicate elif condition |
| `MUTABLE_DEFAULT_STATE_CORRUPTION` | HIGH | Mutable default argument leaks state |
| `SYNTAX_ERROR` | CRITICAL | File won't parse |

**Engler z-score:** `z = (2k - n) / sqrt(n)`. When `k/n >= 0.88` and `z >= 2.0`,
the minority call sites that omit the invariant are flagged as latent bugs.

---

### `review` — Fast-scan differential review

```bash
python3 scripts/council_entry.py review --base HEAD
```

**Output:** Files modified, total LOC delta, Shannon change-dispersion entropy,
risk tier (`FOCUSED_SURGICAL_CHANGE` / `HIGH_DISPERSION_RISK`), anomalies in
changed files.

**Entropy rule:** `H > 2.5 bits` = high dispersion risk (too many files touched).
`H <= 2.5` = focused surgical change.

---

### `forensics` — AST-Refined SZZ bug genealogy

```bash
# Trace line-range evolution
python3 scripts/council_entry.py forensics src/file.ts:40-50

# Trace single line
python3 scripts/council_entry.py forensics src/file.ts:L42

# Trace when a symbol entered/left
python3 scripts/council_entry.py forensics functionName
```

**Output:** Probable Bug-Inducing Commit (BIC), author, date, subject, co-modified
files, evolutionary lineage. Filters out formatting/lint/doc commits.

---

### `dylib-audit` — Native binary audit

```bash
python3 scripts/council_entry.py dylib-audit --path .
```

**Audits:** `.so` (ELF Linux), `.dylib` (Mach-O M1 Pro), `.pyd`, `.dll`
binaries for:
- ISA architecture (`x86_64` vs `aarch64/arm64`)
- Arch-mismatch hazard (host arm64 + binary x86_64)
- Missing shared libraries
- Symbol tables (via `nm`)
- Dependency graphs (via `ldd`/`readelf`)
- String extraction (via `strings`)

**Reports:** `binutils_available` (which tools present), mismatches found.

---

### `cfg` — Control-flow graph extraction

```bash
# Full binary CFG
python3 scripts/council_entry.py cfg /path/to/binary

# Filter to a specific function
python3 scripts/council_entry.py cfg /path/to/binary --function _start
```

**Output:** JSON with nodes (basic blocks), edges (branch/call/fallthrough),
node count, edge count. Uses `objdump -d -M intel` disassembly.

**Verified:** `/bin/true` `_start` → 899 blocks, 1,400 edges in 91.75ms.

---

### `verify-fix` — Separation-Logic Frame Rule verifier

```bash
python3 scripts/council_entry.py verify-fix src/some_file.ts
```

**Checks:**
1. **Liskov signature invariance** across 100% of repo callers
2. No required args increased
3. No max args reduced
4. No kwargs removed/renamed
5. Zero new AST anomalies in patched file

**Verdict:** `SAFE_TO_SHIP` or `BLOCKED_REGRESSION_RISK_DETECTED`.

---

## 3. TOOL LATENT CODEC — `scripts/tool_latent_codec.py`

### `run` — Compress any command output

```bash
# Compress a command's stdout
python3 scripts/council_entry.py run -- git log --oneline -20

# JSON output
python3 scripts/council_entry.py run --json -- pytest tests/

# Output: ASCII BLUF frame + @H-XXXX handle + compression ratio
```

---

### `deref` — Losslessly dereference from a handle

```bash
# View lines 1-30 of a handle's payload
python3 scripts/council_entry.py deref @H-ABCD1234 --lines 1:30

# Grep inside a handle
python3 scripts/council_entry.py deref @H-ABCD1234 --grep "KeyError" --limit 20
```

---

### `bench-compression` — Rate-distortion benchmark

```bash
python3 scripts/council_entry.py bench-compression
```

**Stress test:** Simulates 5,255 pytest collection errors (26,279 lines).

**Results:** 653x compression, 4/4 root-cause classes, 100% coordinate recall,
~298ms CPU encode.

---

### `batch-compress` — Parallel compress multiple files

```bash
python3 scripts/council_entry.py batch-compress logs/pytest.log logs/lint.log logs/git.log --workers 4
```

**Output:** Per-file compression ratio, handle, token counts, overall ratio.

---

## 4. COUNCIL PIPELINE — `scripts/council_pipeline.py`

### `full` — Run complete pipeline end-to-end

```bash
python3 scripts/council_entry.py full --workers 4 \
  --forensics-target "src/file.ts:40-50" \
  --verify-fix-file "src/some_file.ts"
```

**Stages:** sync → hunt → forensics → compress → verify-fix → drift → (ship)

**Duration:** ~800ms for 6 stages.

---

### `receipt-chain` — View chained RCPT receipts

```bash
python3 scripts/council_entry.py receipt-chain
```

---

### `drift` — Cross-repo drift detection

```bash
python3 scripts/council_entry.py drift
```

**7 categories:** app_id, feature_gating, stack_item, renderer_iflet_guard,
lckv_seqlock, launch_guard, ci_rust_toolchain.

---

### `record-fix` — Record fix provenance

```bash
python3 scripts/council_entry.py record-fix \
  --fix-id EL-001 --what "..." --where "..." --why "..." --how "..." \
  --receipt RCPT-XXXX --repos steve
```

---

## 5. Return codes

| Code | Meaning |
|------|---------|
| 0 | Success / PASS |
| 1 | General error / BLOCKED |
| 2 | Usage error (bad args) |

---

## Output format

All commands emit JSON to stdout. The council pipeline wraps each stage with
`[STAGE N]` labels and RCPT receipt IDs. Receipts are tamper-evident and
chained: each stage's receipt can be used as provenance for the next.