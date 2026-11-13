#!/usr/bin/env python3
"""
Lab 12 — Metamorphic Testing Audit (no-oracle testing)

When no ground-truth oracle exists (scientific/numerical code), define
metamorphic relations between inputs and outputs. Any relation violation is a
bug. Solves the "no oracle for scientific code" blind spot.
"""
from __future__ import annotations

import datetime
import json
import random
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def fib(n: int) -> int:
    """Naive Fibonacci (target under test)."""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    return fib(n - 1) + fib(n - 2)


def run_metamorphic_lab() -> dict:
    """Test metamorphic relations on fib() without an exact oracle."""
    t0 = time.time()
    results = {"lab": "metamorphic_testing", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "relations": [], "violations": [], "duration_sec": None}

    random.seed(42)

    # MR1: Fibonacci identity — fib(n+1) == fib(n) + fib(n-1) for n >= 1
    violations = 0
    for _ in range(200):
        n = random.randint(2, 25)
        lhs = fib(n + 1)
        rhs = fib(n) + fib(n - 1)
        if lhs != rhs:
            violations += 1
            if len(results["violations"]) < 10:
                results["violations"].append({"relation": "fib(n+1)==fib(n)+fib(n-1)", "n": n,
                                              "lhs": lhs, "rhs": rhs})
    results["relations"].append({
        "name": "fibonacci_identity",
        "relation": "fib(n+1) == fib(n) + fib(n-1) for n >= 1",
        "tests_run": 200,
        "violations": violations,
    })

    # MR2: Monotonicity — fib(n) < fib(n+1) for n >= 2
    violations = 0
    for _ in range(200):
        n = random.randint(2, 25)
        if fib(n) >= fib(n + 1):
            violations += 1
            if len(results["violations"]) < 10:
                results["violations"].append({"relation": "fib(n) < fib(n+1)", "n": n,
                                              "fib_n": fib(n), "fib_n1": fib(n + 1)})
    results["relations"].append({
        "name": "fibonacci_monotonicity",
        "relation": "fib(n) < fib(n+1) for n >= 2",
        "tests_run": 200,
        "violations": violations,
    })

    # MR3: Even indices — fib(2k) is even when k is a multiple of 3 (every 3rd Fibonacci is even)
    violations = 0
    for _ in range(100):
        k = random.randint(1, 10)
        val = fib(3 * k)
        if val % 2 != 0:
            violations += 1
            if len(results["violations"]) < 10:
                results["violations"].append({"relation": "fib(3k) is even", "k": k, "value": val})
    results["relations"].append({
        "name": "fibonacci_even_every_third",
        "relation": "fib(3k) is even",
        "tests_run": 100,
        "violations": violations,
    })

    total_violations = sum(r["violations"] for r in results["relations"])
    results["summary"] = f"{total_violations} metamorphic relation violations across {len(results['relations'])} relations"
    results["duration_sec"] = round(time.time() - t0, 2)
    return results


if __name__ == "__main__":
    out = run_metamorphic_lab()
    print(json.dumps(out, indent=2))
