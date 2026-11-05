#!/usr/bin/env python3
"""Independent offline arithmetic for the Luma audit; not a renderer benchmark.

Nearest-rank semantics follow the inspected bundled statistics reference. This
module does not import or repair that reference and does not measure a TV.
"""
from __future__ import annotations
import math

MIB = 1024 ** 2


def nearest_rank(values: list[float], percentile: float) -> float | None:
    if not 0 < percentile <= 100 or not math.isfinite(percentile):
        raise ValueError("percentile must be finite and in (0, 100]")
    if any(not math.isfinite(v) for v in values):
        raise ValueError("non-finite sample")
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * percentile / 100) - 1]


def frame_budgets() -> list[dict]:
    return [{"refresh_hz": hz, "period_ms": 1000 / hz} for hz in (24, 30, 50, 60, 75, 90, 120)]


def rgba_bytes(width: int, height: int, buffers: int = 1, samples: int = 1) -> int:
    if any(n <= 0 for n in (width, height, buffers, samples)):
        raise ValueError("dimensions, buffer count and sample count must be positive")
    return width * height * 4 * buffers * samples


def calculations() -> dict:
    surface = []
    for width, height in ((1920, 1080), (3840, 2160)):
        for samples in (1, 4):
            payload = rgba_bytes(width, height, 2, samples)
            surface.append({"width": width, "height": height, "buffers_assumed": 2,
                            "samples_assumed": samples, "rgba_color_payload_bytes": payload,
                            "rgba_color_payload_mib": payload / MIB})
    return {
        "schema": "luma-audit-calculations/1",
        "evidence_class": "INFERRED",
        "not_measurements": True,
        "frame_budgets": frame_budgets(),
        "renderer_soft_budgets_bytes": {"glyph_cpu_geometry": 8*MIB, "text_gpu_geometry": 32*MIB,
                                         "texture_rgba_payload": 48*MIB, "arithmetic_sum_mib": 88},
        "budget_caveat": "Different ownership/memory classes; not total GPU/process memory. Current-frame entries can exceed soft budgets; vector meshes, fonts, decoder memory, driver allocations and framebuffers are additional.",
        "surface_color_payload_scenarios": surface,
        "surface_caveat": "RGBA8 arithmetic only, not actual EGL config/AFBC/MSAA implementation allocation. Excludes resolve/depth/stencil/compositor copies. 4K is experimental.",
        "decoded_icon_max_mib": 256*256*4/MIB,
        "video_rgba_three_buffer_cpu_mib": {f"{w}x{h}": rgba_bytes(w,h,3)/MIB for w,h in ((1920,1080),(3840,2160))},
        "video_nv12_three_buffer_payload_mib": {f"{w}x{h}": w*h*3//2*3/MIB for w,h in ((1920,1080),(3840,2160))},
        "video_caveat": "Hypothetical payloads only. No decoder, zero-copy import, overlay API, protected route or runtime allocation is established.",
        "home_card": {"face": [256,154.4], "pitch": 281.6, "gap": 281.6-256,
                      "baseline_focus_shadow_bounds": [256+2*35,154.4+2*35],
                      "candidate_focus_shadow_bounds": [256+2*43,154.4+2*43],
                      "candidate_extra_width_height": 16,
                      "candidate_shadow_area_ratio": ((256+86)*(154.4+86))/((256+70)*(154.4+70))},
    }

if __name__ == "__main__":
    import json
    print(json.dumps(calculations(), indent=2))
