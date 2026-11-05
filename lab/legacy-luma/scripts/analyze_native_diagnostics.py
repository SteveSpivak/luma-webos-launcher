#!/usr/bin/env python3
"""Offline p99/spike analysis of existing Luma --diagnostics JSON.

No rendering, device access or new collector. Missing native data stays UNKNOWN.
Spike/component association is not causal attribution or GPU timing.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path


def nearest_rank(samples: list[float], p: float) -> float:
    if not samples or not math.isfinite(p) or not 0 < p <= 100:
        raise ValueError("Nonempty samples and percentile in (0,100] are required")
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in samples):
        raise ValueError("Frame intervals must be finite positive milliseconds")
    ordered = sorted(samples)
    return ordered[math.ceil(p / 100 * len(ordered)) - 1]


def analyze(report: dict, evidence_class: str = "UNVERIFIED_INPUT") -> dict:
    profile = report.get("profile")
    if not isinstance(profile, dict) or not isinstance(profile.get("timeline"), list) or not profile["timeline"]:
        return {"schema": "luma-diagnostics-analysis/1", "status": "UNKNOWN", "evidence_class": evidence_class,
                "reason": "No profiled presentation timeline; idle loops are not frames", "p99_ms": None,
                "gpu_time_ms": None, "gpu_memory_bytes": None,
                "focus_latency": {"status": "UNKNOWN", "reason": "Native focus traces not present"}}
    frames = profile["timeline"]
    intervals = []
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("Timeline entries must be objects")
        intervals.append(frame.get("interval_ms"))
    p99 = nearest_rank(intervals, 99)
    native_p99 = (profile.get("pacing") or {}).get("p99_ms")
    top = sorted(frames, key=lambda f: f["interval_ms"], reverse=True)[:5]
    spikes = [{"interval_ms": f["interval_ms"], "compose_ms": f.get("compose_ms"), "render_ms": f.get("render_ms"),
               "swap_ms": f.get("swap_ms"), "glyph_ms": f.get("glyph_ms"), "vector_ms": f.get("vector_ms"),
               "image_ms": f.get("image_ms"), "redrawn": f.get("redrawn")} for f in top]
    focus = report.get("focus_latency_ms")
    focus_summary = None
    if isinstance(focus, list) and focus:
        focus_summary = {"samples": len(focus), "p95_ms": nearest_rank(focus, 95), "p99_ms": nearest_rank(focus, 99),
                         "meaning": "input dequeue to first corresponding swap call, not photons"}
    return {"schema": "luma-diagnostics-analysis/1", "status": "ANALYZED", "evidence_class": evidence_class,
            "samples": len(intervals), "p50_ms": nearest_rank(intervals, 50), "p95_ms": nearest_rank(intervals, 95),
            "p99_ms": p99, "max_ms": max(intervals), "native_p99_matches": None if native_p99 is None else native_p99 == p99,
            "top_interval_associations": spikes, "attribution": "ASSOCIATION_NOT_CAUSATION",
            "focus_latency": focus_summary or {"status": "UNKNOWN", "reason": "Native focus traces not present"},
            "gpu_time_ms": None, "gpu_memory_bytes": None,
            "caveat": "CPU-side presentation-call cadence; not hardware present, GPU completion or physical-TV evidence."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--evidence-class", default="UNVERIFIED_INPUT")
    args = parser.parse_args()
    result = analyze(json.loads(args.input.read_text()), args.evidence_class)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "p99_ms": result["p99_ms"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
