# FORENSICS & REVERSE ENGINEERING

Binary analysis, control-flow graphs, symbol tables, dependency graphs, and
bug genealogy — all zero-external-dependency (pure Python) with optional
binutils enhancement.

---

## 1. Control-Flow Graph (CFG) extraction — `cfg` subcommand

```bash
python3 scripts/council_entry.py cfg /path/to/binary --function function_name
```

### How it works

1. **Disassemble** with `objdump -d -M intel` (Intel syntax for readability)
2. **Parse** instruction lines into address/mnemonic/operand tuples
3. **Partition** into basic blocks — maximal sequences with one entry and one exit
4. **Identify terminators** — `jmp`, `jcc`, `call`, `ret`, and architecture-specific variants
5. **Build edges** — branch_taken, fallthrough, call, unconditional
6. **Resolve targets** — direct addresses and PLT stubs

### Terminators detected

| Architecture | Instructions |
|--------------|-------------|
| x86-64 | `jmp`, `ret`, `call`, `je/jne/jz/jnz/...`, `jmp*`, `call*` |
| aarch64 | `b`, `bl`, `blr`, `ret`, `cbz/cbnz`, `tbz/tbnz`, `b.eq/b.ne/...` |

### Output example

```json
{
  "binary": "/bin/true",
  "cfg": {
    "node_count": 899,
    "edge_count": 1400,
    "nodes": [
      {"id": "B0000000000002000", "start_addr": "2000", "instruction_count": 1, "terminator": "je 2012"},
      {"id": "B2010", "start_addr": "2010", "instruction_count": 1, "terminator": "call rax"},
      {"id": "B2012", "start_addr": "2012", "instruction_count": 1, "terminator": "ret"}
    ],
    "edges": [
      {"from": "B2000", "to": "B2012", "type": "branch_taken"},
      {"from": "B2000", "to": "B2010", "type": "fallthrough"}
    ]
  }
}
```

**Verified:** `/bin/true` `_start` → 899 blocks, 1,400 edges in 91.75ms.

---

## 2. Native binary audit — `dylib-audit` subcommand

```bash
python3 scripts/council_entry.py dylib-audit --path .
```

### What it checks

| Check | Linux (.so ELF) | macOS (.dylib Mach-O) |
|-------|----------------|----------------------|
| Magic header | `\x7fELF` | `0xfeedfacf` / `0xcafebabe` |
| Bit class | 32/64-bit | 64-bit |
| Endianness | Little/Big | Native |
| ISA | `x86_64` / `aarch64` / `x86` | `x86_64` / `arm64` |
| Entry point | Hex address | N/A |
| Missing libs | `ldd` "not found" | `otool -L` missing |
| Arch mismatch | host arm64 + binary x86_64 | Same |
| Symbol table | `nm --defined-only` | Same |
| Dependency graph | `ldd` / `readelf -d` | `otool -L` |
| String extraction | `strings -n 4` | Same |

### binutils availability

The output includes `binutils_available` showing which of
`nm`, `objdump`, `readelf`, `strings`, `ldd` are present. Without them,
only raw header parsing works (still useful for ISA detection).

---

## 3. AST-Refined SZZ bug genealogy — `forensics` subcommand

```bash
# Trace line-range evolution
python3 scripts/council_entry.py forensics src/file.ts:40-50

# Trace a symbol's history
python3 scripts/council_entry.py forensics functionName
```

### How SZZ works here

1. **`git log -L start,end:file`** — line-range evolution tracking
2. **`git log -S symbol`** — pickaxe search for when a symbol entered/left
3. **Filter** — skip formatting/lint/doc/comment-only commits
4. **BIC identification** — the earliest non-trivial commit touching the defective lines
5. **Co-modified files** — `git show --name-only` for each candidate commit

### Output

```json
{
  "forensic_target": "src/file.ts:40-50",
  "probable_bug_inducing_commit_BIC": {
    "commit_sha": "303691e",
    "date": "2026-10-XX",
    "author": "...",
    "subject": "...",
    "co_modified_files_in_commit": [...],
    "is_probable_bug_inducing_commit": true
  },
  "evolutionary_lineage": [...]
}
```

---

## 4. Engler statistical deviance mining (in `hunt`)

When no formal specification exists, mine implicit invariants from majority
behavior:

**z-score formula:** `z = (2k - n) / sqrt(n)`

Where:
- `n` = total call sites of a function
- `k` = call sites enforcing invariant `I` (e.g., checking return value, wrapping in try/except)

**Decision rule:** When `n >= 5`, `k/n >= 0.88`, and `z >= 2.0`, the
`(n - k)` call sites that omit invariant `I` are flagged as high-probability
latent bugs.

**Invariants mined:**
- Return value usage (88% threshold)
- try/except guarding (85% threshold)

---

## 4. PVS-Studio structural patterns (in `hunt`)

Zero-config AST pattern detection:

| Pattern | Severity | Meaning |
|---------|----------|---------|
| `x == x` | HIGH | Tautological comparison (copy-paste slip) |
| `a and a` | HIGH | Redundant boolean subexpression |
| Duplicate `elif` | HIGH | Dead branch |
| Mutable default arg | HIGH | State leaks across calls |

---

## 5. Separation-Logic Frame Rule — `verify-fix` subcommand

**Theory:** `{P * R} C → C' {Q * R}` — a patch `C → C'` is safe only if
the disjoint frame `R` (all callers outside the fix) shows zero behavioral
drift.

**Mechanical checks:**
1. Required positional args did not increase
2. Max accepted positional args did not decrease
3. No kwargs removed or renamed (unless `**kwargs` present)
4. No symbols deleted
5. Zero new AST anomalies in patched file

**Verdict:** `SAFE_TO_SHIP` or `BLOCKED_REGRESSION_RISK_DETECTED`.

---

## 6. Math & physics foundations

| Domain | Concept | Application in kit |
|--------|---------|-------------------|
| Information theory | Shannon self-information `I(l) = -log2 P(template)` | Surprisal-weighted line elision in latent codec |
| Rate-distortion | `R(D) = min I(X;X̂)` s.t. `E[d(X,X̂)] ≤ D` | Compression vs fidelity tradeoff |
| Statistics | Binomial z-score | Engler deviance mining |
| Graph theory | Basic blocks + CFG edges | Control-flow graph extraction |
| Separation logic | Frame rule `*` | Zero-regression patch verification |
| Information bottleneck | `I(X;Z) - β·I(Z;Y)` | What to preserve vs compress |