"""Deterministic arithmetic for comparing this fork with the upstream launcher.

Every function here is pure: no filesystem, network, clock, environment or GPU
access. Nothing in this module measures a device. The functions model geometry
and motion constants that are read from pinned source files by
``compare_reference_launcher.py``; results are labelled MODEL, never MEASURED.

Shadow model, from ``src/renderer.rs`` and ``src/damage.rs`` in both trees:

* a ``Draw::Shadow(rect, radius, blur, color)`` is drawn as a *quad* expanded by
  ``blur`` on every side (``rect.inset(-blur)``);
* its alpha is ``1 - smoothstep(-blur, blur, d)`` for the signed distance ``d``
  to the rounded rect, i.e. a penumbra band of width ``2 * blur`` centred on
  the shape edge;
* damage for the same draw is the rect expanded by ``blur + 1``.

So fill cost grows as ``(w + 2b)(h + 2b)`` and the softness is governed by
``blur`` while the "float" of a card is governed by the vertical offset.
"""

from __future__ import annotations

import math

#: Apps/Home card geometry used by the focus-depth experiment and its tests.
CARD_W = 256.0
CARD_H = 154.4
CARD_RADIUS = 19.2

#: Bytes per RGBA8 pixel and per full 1080p frame.
RGBA8_BPP = 4
FRAME_1080P_PX = 1920 * 1080
FRAME_4K_PX = 3840 * 2160


def rgba_bytes(width: float, height: float, bpp: int = RGBA8_BPP) -> float:
    """Bytes for one uncompressed RGBA surface."""
    return width * height * bpp


def shadow_quad(width: float, height: float, blur: float) -> float:
    """Rasterised area of a blurred rounded-rect shadow quad, in pixels."""
    if blur < 0 or width <= 0 or height <= 0:
        raise ValueError("Positive geometry and non-negative blur are required")
    return (width + 2 * blur) * (height + 2 * blur)


def penumbra_ring(width: float, height: float, blur: float) -> float:
    """Area of the soft band only: shadow quad minus the card face."""
    return shadow_quad(width, height, blur) - width * height


def damage_area(width: float, height: float, blur: float) -> float:
    """Dirty-rect area for one shadow, using the ``blur + 1`` damage rule."""
    return (width + 2 * (blur + 1)) * (height + 2 * (blur + 1))


def zoom_area_factor(zoom: float) -> float:
    """Area multiplier of an isotropic scale about the rect centre."""
    return zoom * zoom


def depth_index(offset_y: float, height: float = CARD_H) -> float:
    """Vertical shadow offset as a fraction of card height (dimensionless)."""
    return offset_y / height


def softness(blur: float, height: float = CARD_H) -> float:
    """Penumbra half-width as a fraction of card height (dimensionless)."""
    return blur / height


def penumbra_span(blur: float, height: float = CARD_H) -> float:
    """Full penumbra band width as a fraction of card height."""
    return 2 * blur / height


def contrast(blur: float, offset_y: float) -> float:
    """Softness-to-depth ratio; above ~3 reads as a halo, below ~2 as a cast."""
    if offset_y <= 0:
        raise ValueError("A positive vertical offset is required")
    return blur / offset_y


def composite_alpha(*alphas: float) -> float:
    """Alpha of stacked, non-premultiplied black layers over a background."""
    remaining = 1.0
    for alpha in alphas:
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("Alphas must be within [0, 1]")
        remaining *= 1.0 - alpha
    return 1.0 - remaining


def chase_rate(scroll: float = 0.180, gain: float = 3.22) -> float:
    """Exponential follow rate used by ``motion::chase`` (per second)."""
    if scroll <= 0:
        raise ValueError("Scroll duration must be positive")
    return gain / scroll


def chase_tau(scroll: float = 0.180, gain: float = 3.22) -> float:
    """Time constant of ``motion::chase`` in seconds."""
    return 1.0 / chase_rate(scroll, gain)


def chase_settle(fraction: float, scroll: float = 0.180, gain: float = 3.22) -> float:
    """Seconds for ``motion::chase`` to cover ``fraction`` of the remaining gap."""
    if not 0.0 < fraction < 1.0:
        raise ValueError("Fraction must be within (0, 1)")
    return -math.log(1.0 - fraction) / chase_rate(scroll, gain)


def pop(k: float, decay: float = 5.0, freq: float = 10.0) -> float:
    """Focus spring curve ``1 - exp(-decay*k) * cos(freq*k)`` from ``state.rs``."""
    return 1.0 - math.exp(-decay * k) * math.cos(freq * k)


def pop_peak_k(decay: float = 5.0, freq: float = 10.0) -> float:
    """Normalised time of the first turning point of the focus spring."""
    if decay <= 0 or freq <= 0:
        raise ValueError("Decay and frequency must be positive")
    return (math.pi - math.atan(decay / freq)) / freq


def pop_peak(decay: float = 5.0, freq: float = 10.0) -> float:
    """Peak value of the focus spring (1.0 is the settled target)."""
    return pop(pop_peak_k(decay, freq), decay, freq)


def equivalent_damping(overshoot: float) -> float:
    """Damping ratio of a true second-order step with the same overshoot."""
    if not 0.0 < overshoot < 1.0:
        raise ValueError("Overshoot must be within (0, 1)")
    return 1.0 / math.sqrt(1.0 + (math.pi / math.log(1.0 / overshoot)) ** 2)


def pop_settle_k(decay: float = 5.0, epsilon: float = 0.01) -> float:
    """Normalised time at which the spring envelope falls below ``epsilon``."""
    if decay <= 0 or not 0.0 < epsilon < 1.0:
        raise ValueError("Positive decay and epsilon within (0, 1) are required")
    return math.log(1.0 / epsilon) / decay


def fill_bytes(area_px: float, bpp: int = RGBA8_BPP, traffic: float = 1.0) -> float:
    """Bytes touched by filling ``area_px``; ``traffic`` models read+write."""
    return area_px * bpp * traffic


def bandwidth_gbs(bytes_per_frame: float, hz: float) -> float:
    """Gigabytes per second implied by a per-frame byte count at ``hz``."""
    if hz <= 0:
        raise ValueError("Refresh rate must be positive")
    return bytes_per_frame * hz / 1e9


def grid_shadow_area(
    resting: int,
    focused: int,
    resting_blur: float,
    focused_blur: float,
    glow: float = 0.0,
    width: float = CARD_W,
    height: float = CARD_H,
) -> float:
    """Shadow fill for a grid of ``resting + focused`` cards.

    ``glow`` is an extra halo area per focused card (upstream draws a second,
    much wider shadow). Passing ``resting_blur=0`` models upstream's Apps-page
    optimisation that skips resting-card shadows entirely.
    """
    if resting < 0 or focused < 0:
        raise ValueError("Card counts cannot be negative")
    resting_area = 0.0 if resting_blur == 0 else shadow_quad(width, height, resting_blur)
    focused_area = shadow_quad(width, height, focused_blur) + glow
    return resting * resting_area + focused * focused_area
