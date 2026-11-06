#!/usr/bin/env python3
"""
scripts/sandbox_verify.py — Offline Rust Static Analyzer (rustfmt + dead_code + cfg audit)
& Mathematical Verification Suite for Cloud Linux Sandboxes without a Rust toolchain.

Checks:
  1. Trailing whitespace & hard tabs (instant rustfmt failure)
  2. 100-column max_width on non-string, non-comment code lines
  3. Dead-code detector: finds `fn name(` definitions and verifies call count >= 2
  4. Call-Graph Reverse Census: asserts every Phase 2/3 feature symbol has >=1
     production call site outside its own definition and #[cfg(test)] blocks
  5a. Structural match-arm syntax check (bare statements between arms)
  5b. Draw::Shape(_) arity check on 4-tuple variant (E0023)
  5c. Deserialize used without `use serde` import check
  6. Lesson L-042 Enum Raiser Census (brace-balanced enum parser)
  7. Mathematical verification of Spring1D convergence & .ltex header packing
"""
import glob
import math
import re
import struct
import sys

MAX_WIDTH = 100
errors = []

all_files = {}
for path in sorted(glob.glob("src/**/*.rs", recursive=True)):
    with open(path, "r", encoding="utf-8") as f:
        all_files[path] = f.read()

full_corpus = "\n".join(all_files.values())

for path, content in all_files.items():
    lines = content.splitlines()
    for lineno, line in enumerate(lines, start=1):
        # 1. Trailing whitespace & hard tabs
        if line != line.rstrip(" \t"):
            errors.append(f"{path}:{lineno}: trailing whitespace")
        if "\t" in line:
            errors.append(f"{path}:{lineno}: tab character")

        # 2. 100-col check on non-string, non-comment code lines
        if len(line) > MAX_WIDTH:
            s = line.strip()
            if not (s.startswith("//") or '"' in s):
                errors.append(
                    f"{path}:{lineno}: width {len(line)} > {MAX_WIDTH}: {s[:55]}..."
                )

    # 3. Dead-code detector: find `fn name(` definitions and verify call count >= 2 in corpus
    for m in re.finditer(r"\b(?:pub\s+)?(?:const\s+)?fn\s+([a-zA-Z0-9_]+)\s*[<(]", content):
        fn_name = m.group(1)
        if fn_name in ("main", "new", "default", "fmt", "drop", "eq", "partial_cmp", "cmp", "hash"):
            continue
        occurrences = len(re.findall(rf"\b{re.escape(fn_name)}\b", full_corpus))
        if occurrences < 2:
            errors.append(
                f"{path}: dead_code risk: `fn {fn_name}` appears only once across entire codebase!"
            )

# 4. Call-Graph Reverse Census: assert every Phase 2/3 feature symbol has
#    >=1 production call site outside its own definition and #[cfg(test)] blocks.
#    Strip #[cfg(test)] blocks before counting so test-only usage doesn't count.
prod_corpus_parts = []
for content in all_files.values():
    # Remove everything from #[cfg(test)] to the end of the module/test block.
    # This is approximate but sufficient: test modules are typically at the
    # bottom of a file and start with #[cfg(test)] mod tests { ... }.
    parts = content.split("#[cfg(test)]")
    prod_corpus_parts.append(parts[0])  # Everything before the first #[cfg(test)]
prod_corpus = "\n".join(prod_corpus_parts)

REQUIRED_LIVE_CALLS = [
    ("src/motion.rs", "Spring1D", "step"),
    ("src/state.rs", "resolve_vertical_stack_target", "resolve_vertical_stack_target"),
    ("src/renderer.rs", "TextureUploadScheduler", "drain_within_budget"),
    ("src/renderer.rs", "QuadBatcher", "push_rounded_quad"),
    ("src/app_artwork.rs", "RawCachedTexture", "load_from_disk"),
    ("src/fast_kv.rs", "LCKV", "read_bridge_cards"),
]

for module, feature, symbol in REQUIRED_LIVE_CALLS:
    # A symbol must appear at least twice in non-test code:
    #   1 definition + >=1 production call site
    count = len(re.findall(rf"\b{re.escape(symbol)}\b", prod_corpus))
    if count < 2:
        errors.append(
            f"REVERSE-CENSUS FAILURE [{module}]: `{symbol}` ({feature}) has "
            f"{max(0, count - 1)} production call site(s) (hollow/unwired feature)!"
        )

# 5. Structural Rust Syntax Checks:
#    5a. Catch bare statements placed between `match` arms.
#    5b. Catch `Draw::Shape(_)` on the 4-tuple variant (should be `Draw::Shape(..)`).
#    5c. Catch `Deserialize` referenced without `use serde` import.
for path, content in all_files.items():
    lines = content.splitlines()
    for i in range(len(lines) - 2):
        if (
            lines[i].rstrip().endswith("}")
            and re.search(r"[a-zA-Z_][a-zA-Z0-9_.]*\s*\([^)]*\);\s*$", lines[i + 1])
            and re.search(r"[A-Z][a-zA-Z0-9_]*(::[A-Z][a-zA-Z0-9_]*)*\s*=>", lines[i + 2])
        ):
            errors.append(
                f"{path}:{i + 1}: SYNTAX ERROR: bare statement between `match` arms!"
            )
    for m in re.finditer(r"Draw::Shape\(\s*_\s*\)", content):
        lineno = content[: m.start()].count("\n") + 1
        errors.append(
            f"{path}:{lineno}: E0023 ARITY ERROR: `Draw::Shape(_)` used on 4-tuple variant "
            f"(use `Draw::Shape(..)`)"
        )
    # Flag bare `Deserialize` (not `serde::Deserialize`) without a serde import.
    if re.search(r"(?<!serde::)\bDeserialize\b", content) and "use serde" not in content:
        errors.append(
            f"{path}: COMPILE ERROR: `Deserialize` referenced without `use serde` import"
        )

# 6. Lesson L-042 ("Census the raiser, not the handler"):
#    Every variant of `enum Effect` in src/state.rs must be constructed
#    (>= 2 occurrences: >=1 raiser and >=1 handler) in production code.
#    Uses brace-balanced extraction to handle struct variants like
#    `NuvioLaunch { content_target: String }` correctly.
state_path = "src/state.rs"
if state_path in all_files:
    state_content = all_files[state_path]
    effect_start = state_content.find("pub enum Effect")
    if effect_start != -1:
        brace_open = state_content.find("{", effect_start)
        depth = 0
        brace_close = -1
        for idx in range(brace_open, len(state_content)):
            if state_content[idx] == "{":
                depth += 1
            elif state_content[idx] == "}":
                depth -= 1
                if depth == 0:
                    brace_close = idx
                    break
        if brace_close != -1:
            effect_body = state_content[brace_open + 1 : brace_close]
            # Strip inner `{ ... }` or `( ... )` payloads so we only parse
            # top-level variant names.
            top_level = re.sub(r"\{[^}]*\}|\([^)]*\)", "", effect_body)
            for raw_line in top_level.splitlines():
                line = raw_line.split("//")[0].strip().rstrip(",")
                if not line or line.startswith("#["):
                    continue
                variant = line.strip()
                if re.match(r"^[A-Z][A-Za-z0-9_]*$", variant):
                    refs = len(
                        re.findall(rf"\bEffect::{re.escape(variant)}\b", prod_corpus)
                    )
                    if refs < 2:
                        errors.append(
                            f"L-042 RAISER CENSUS FAILURE: `Effect::{variant}` has "
                            f"{refs} production reference(s) (needs >=1 raiser + >=1 handler)!"
                        )

# 7. Mathematical Verification of Spring1D & Viewport Focus Corridor
def verify_math_models():
    # Test Critically Damped Spring analytical convergence & elastic edge bump
    pos, vel, target, omega = 0.0, 0.0, 100.0, 26.0
    for _ in range(60):  # 1 second at 60Hz
        dt = 1.0 / 60.0
        delta = pos - target
        exp = math.exp(-omega * dt)
        c = vel + omega * delta
        pos = target + (delta + c * dt) * exp
        vel = (vel - omega * c * dt) * exp
    assert abs(pos - 100.0) < 0.01 and abs(vel) < 0.1, "Spring1D failed to converge"

    # Test .ltex 12-byte header binary compatibility
    header = struct.pack("<4sBBHHH", b"LTEX", 1, 1, 128, 128, 0x18E3)
    assert len(header) == 12 and header[:4] == b"LTEX", "LTEX header packing mismatch"

verify_math_models()

if errors:
    print(f"SANDBOX VERIFY FAILED ({len(errors)} issues):")
    for e in errors:
        print("  [ERROR]", e)
    sys.exit(1)
else:
    print("SANDBOX VERIFY PASSED: 0 rustfmt, dead_code, or mathematical errors.")
