# QUICK START — 5 minutes to your first Council run

This guide walks you from a fresh clone of **ecklf/lg-luma** (or any repo) to
a full Council forensics + bug-hunting + compression run.

---

## Step 0: Prerequisites

```bash
# Python 3.11+ (stdlib only — no pip install required for the CLIs)
python3 --version

# Optional but recommended for reverse engineering (binutils):
#   nm, objdump, readelf, strings, ldd
which nm objdump readelf strings ldd
```

All CLIs are pure Python 3.11 stdlib. They work without any of the binutils,
but `dylib-audit` and `cfg` are much richer with them.

---

## Step 1: Clone your target repo

```bash
git clone https://github.com/ecklf/lg-luma.git my-luma
cd my-luma
```

> **Note:** The Council tools are language-agnostic. They work on TypeScript,
> JavaScript, Rust, Python, Go, C/C++, SQL, and shell. The examples below use
> the ecklf/lg-luma repo (TypeScript/Web) but apply to any repo.

---

## Step 2: Copy the starter kit

```bash
# Copy everything from the starter kit into your repo
cp -r /path/to/COUNCIL_STARTER_KIT/* .

# Make scripts executable
chmod +x scripts/*.py

# Verify
ls scripts/
# council_entry.py  nexus_agent_os.py  tool_latent_codec.py  aegis_bug_hunter.py  council_pipeline.py
```

---

## Step 3: Run the full pipeline (one command)

```bash
python3 scripts/council_entry.py full
```

This runs all 6 stages in ~800ms:

| Stage | Command | What it does |
|-------|---------|--------------|
| 1 | `sync` | Indexes all source files (symbols, edges, state channels, import traps) |
| 2 | `hunt` | Finds bugs via Engler deviance mining + PVS-Studio AST patterns |
| 3 | `forensics` | Traces bug genealogy via AST-Refined SZZ (Bug-Inducing Commit) |
| 4 | `run` | Compresses tool output into @H-XXXX epistemic handles |
| 5 | `verify-fix` | Proves a patch breaks 0 callers (Frame Rule + Liskov) |
| 6 | `drift` | Detects cross-repo drift across 7 categories |

Expected output: all stages PASS, RCPT receipts issued for each.

---

## Step 4: Hunt for bugs in your code

```bash
# Scan the whole repo
python3 scripts/council_entry.py hunt

# Scan a specific directory
python3 scripts/council_entry.py hunt --path src/

# Output: JSON with anomalies ranked by severity (CRITICAL > HIGH > MEDIUM > LOW)
```

Example anomaly types found:
- `CALL_ARITY_MISMATCH_TYPEERROR` — wrong argument count
- `UNAWAITED_ASYNC_COROUTINE` — async coroutine dropped
- `ENGLER_DEVIANT_IGNORED_RETURN` — return value ignored (statistical outlier)
- `ENGLER_DEVIANT_UNGUARDED_CALL` — missing try/except (statistical outlier)
- `TAUTOLOGICAL_COMPARISON_COPY_PASTE` — `x == x` (copy-paste slip)
- `MUTABLE_DEFAULT_STATE_CORRUPTION` — mutable default argument

---

## Step 5: Compress noisy tool output

```bash
# Compress any command's output into a compact @H-XXXX handle
python3 scripts/council_entry.py run -- npm test 2>&1 | head -5

# Or directly on a log file
python3 scripts/tool_latent_codec.py batch-compress logs/pytest.log logs/lint.log

# Losslessly dereference lines from a handle later
python3 scripts/council_entry.py deref @H-ABCD1234 --lines 1:50
```

Typical results: **653x compression** on a 5,255-error stress test, 100%
coordinate recall (no blurred line numbers or hashes).

---

## Step 6: Verify a fix is regression-free

Before committing a fix:

```bash
# Make your edit to src/some_file.js, then:
python3 scripts/council_entry.py verify-fix src/some_file.js
```

The verifier checks:
1. **Liskov signature invariance** — no new required args, no removed kwargs
2. **Zero new AST anomalies** — no tautologies, dead branches, mutable defaults
3. **Verdict**: `SAFE_TO_SHIP` or `BLOCKED_REGRESSION_RISK_DETECTED`

---

## Step 7: Record fix provenance

After a fix is verified:

```bash
python3 scripts/council_entry.py record-fix \
  --fix-id EL-001 \
  --what "Fixed null dereference in parser" \
  --where "src/parser.ts:42" \
  --why "Engler deviance mining found unguarded return at call site" \
  --how "Added null check + regression test" \
  --receipt RCPT-XXXX
```

This logs what/where/why/how for cross-repo patch alignment.

---

## Next steps

- Read `CLI_REFERENCE.md` for every command and flag
- Read `CROSS_ENVIRONMENT.md` for macOS / Linux / webOS setup
- Read `MEASUREMENT.md` for all benchmarks and SLAs
- Read `FORENSICS_RE.md` for reverse engineering details
- Read `LESSONS_LEARNED.md` for what worked and what didn't