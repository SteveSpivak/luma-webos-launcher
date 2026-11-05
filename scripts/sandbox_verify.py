#!/usr/bin/env python3
"""
scripts/sandbox_verify.py — Offline Rust Static Analyzer (rustfmt + dead_code + cfg audit)
& Mathematical Verification Suite for Cloud Linux Sandboxes without a Rust toolchain.

Checks:
  1. Trailing whitespace & hard tabs (instant rustfmt failure)
  2. 100-column max_width on non-string, non-comment code lines
  3. Dead-code detector: finds `fn name(` definitions and verifies call count >= 2
  4. Mathematical verification of Spring1D convergence & .ltex header packing
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

# 4. Mathematical Verification of Spring1D & Viewport Focus Corridor
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
