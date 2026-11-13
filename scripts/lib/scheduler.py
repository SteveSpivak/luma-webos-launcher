"""
scripts/lib/scheduler.py — MiMo memory admission + Graham's LPT scheduler.

Computes the optimal safe worker count W* using the stochastic memory admission
equation, then schedules tests longest-processing-time-first to eliminate tail
stragglers. Pure stdlib, cross-platform.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class HardwareTelemetry:
    effective_cores: int
    avail_ram_mb: float
    ram_scratch_root: str
    p_cores: int = 0
    e_cores: int = 0


@dataclass
class TestItem:
    rel_path: str
    merkle: str
    est_duration_s: float
    slot_id: int = 0


def mimo_worker_count(hw: HardwareTelemetry, est_worker_mb: float = 140.0,
                      override: int | None = None) -> int:
    """MiMo's stochastic memory admission equation for W*.

    W* = max(1, min(C_eff, floor((M_budget - M_parent) / (mu_worker + 1.65*sigma_worker))))
    Conservative: sigma assumed 20% of mean when no history exists.
    """
    if override:
        return max(1, override)

    mu = est_worker_mb
    sigma = 0.20 * mu
    safe_ram_mb = max(128.0, hw.avail_ram_mb * 0.80 - 150.0)
    ram_capped = max(1, int(safe_ram_mb // (mu + 1.65 * sigma)))
    return max(1, min(hw.effective_cores, ram_capped))


def lpt_sort(tests: list[TestItem]) -> list[TestItem]:
    """Graham's Longest Processing Time First sort (descending est duration)."""
    return sorted(tests, key=lambda t: t.est_duration_s, reverse=True)


def bin_pack(tests: list[TestItem], workers: int) -> list[list[TestItem]]:
    """LPT bin-packing: assign each test to the currently-least-loaded worker."""
    bins: list[list[TestItem]] = [[] for _ in range(workers)]
    loads = [0.0 for _ in range(workers)]
    for t in tests:
        least = min(range(workers), key=lambda i: loads[i])
        bins[least].append(t)
        loads[least] += t.est_duration_s
    return bins
