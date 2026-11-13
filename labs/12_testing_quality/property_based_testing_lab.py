#!/usr/bin/env python3
"""
Lab 12 — Property-Based Testing Audit (hypothesis)

Specifies invariants (not examples) for target functions and lets Hypothesis
generate hundreds of random inputs per property, shrinking failures to minimal
reproducers automatically. Solves the "hand-picked examples miss edge cases"
blind spot.
"""
from __future__ import annotations

import contextlib
import datetime
import io
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_property_based_lab() -> dict:
    """Run property-based tests against target pure functions with Hypothesis."""
    from hypothesis import given, strategies as st, HealthCheck, settings

    t0 = time.time()
    results = {
        "lab": "property_based_testing",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "properties": [],
        "failures": [],
        "duration_sec": None,
    }

    # --- Property implementations (local to this function) ---

    @given(st.lists(st.integers(min_value=-1000, max_value=1000), min_size=0, max_size=50))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def prop_sort_idempotent(xs):
        result = sorted(xs)
        assert sorted(result) == result, f"sort not idempotent: {result}"

    @given(st.lists(st.integers(min_value=-1000, max_value=1000), min_size=0, max_size=50))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def prop_reverse_sort_commute(xs):
        result1 = sorted(xs, reverse=True)
        result2 = sorted(xs)[::-1]
        assert result1 == result2, f"reverse/sort commutativity violated: {result1} vs {result2}"

    @given(st.lists(st.integers(min_value=-1000, max_value=1000), min_size=0, max_size=100))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def prop_sort_preserves_length(xs):
        assert len(sorted(xs)) == len(xs), f"sort changed length: {len(xs)} -> {len(sorted(xs))}"

    # Map property name -> function (avoid globals() lookup bug for local funcs)
    prop_map = {
        "sort_idempotent": prop_sort_idempotent,
        "reverse_sort_commute": prop_reverse_sort_commute,
        "sort_preserves_length": prop_sort_preserves_length,
    }

    descriptions = {
        "sort_idempotent": "sort(sort(x)) == sort(x)",
        "reverse_sort_commute": "sort(x, reverse=True) == sort(x)[::-1]",
        "sort_preserves_length": "len(sort(x)) == len(x)",
    }

    for prop_name, func in prop_map.items():
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                func()
            results["properties"].append(f"{prop_name}: PASSED (200 examples)")
        except AssertionError as e:
            results["failures"].append({"property": prop_name, "error": str(e)[:200]})
            results["properties"].append(f"{prop_name}: FAILED — {str(e)[:100]}")
        except Exception as e:
            results["failures"].append({"property": prop_name, "error": type(e).__name__ + ": " + str(e)[:200]})
            results["properties"].append(f"{prop_name}: ERROR — {type(e).__name__}")

    results["duration_sec"] = round(time.time() - t0, 2)
    results["summary"] = f"{3 - len(results['failures'])}/3 properties passed"
    return results


if __name__ == "__main__":
    import json
    out = run_property_based_lab()
    print(json.dumps(out, indent=2))
