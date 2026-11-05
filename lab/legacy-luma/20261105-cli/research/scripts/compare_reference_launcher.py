#!/usr/bin/env python3
"""Collect pinned forensic facts about the upstream launcher fork.

Read-only. The reference tree is never imported into this checkout: it is
cloned outside Git (``/home/user/luma-ref``), checked against an exact commit,
and only counts, file names, constants and line numbers are recorded.

Exit codes: 0 facts written, 2 reference missing or wrong pin.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reference_launcher as math_model  # noqa: E402

PIN = "40994fc144b5af481056d14e2fb93304aa1e2c82"
REFERENCE = "funnymataleao/luma-webos-launcher"
OUR_BASE = "e5608cd053be5376a54a806129a332952dfabcef"
AREAS = ("src", "tools", "tests", "tv", "vector-geometry", "docs", ".github", ".changeset", "native", "extras", "assets")
TEXT_EXT = {".rs", ".c", ".h", ".cpp", ".mjs", ".js", ".json", ".md", ".toml", ".sh", ".html", ".css", ".txt", ".nix", ".yml", ".yaml", ".patch"}
BINARY_EXT = {".ttf", ".otf", ".woff", ".woff2", ".jpg", ".jpeg", ".png", ".webp", ".ipk", ".so", ".a", ".ico", ".gif", ".zip"}

#: Hygiene probes. Only counts are recorded; matched text is never emitted.
SECRET_PATTERNS = {
    "private_key_block": r"BEGIN [A-Z ]*PRIVATE KEY",
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "github_token": r"ghp_[A-Za-z0-9]{20,}",
    "slack_token": r"xox[bap]-[A-Za-z0-9-]{10,}",
    "jwt_literal": r"eyJ[A-Za-z0-9_-]{20,}\.",
    "assigned_password": r"password\s*[:=]\s*['\"][^'\"]{4,}",
}
DRM_PATTERNS = {"widevine": r"(?i)widevine", "playready": r"(?i)playready", "hdcp": r"(?i)hdcp", "drm": r"(?i)\bdrm\b"}


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {result.stderr}")
    return result.stdout


def tree_entries(repo: Path, rev: str = "HEAD") -> dict[str, str]:
    """Object ids of a tree, always pinned to an explicit revision."""
    entries = {}
    for line in git(repo, "ls-tree", "-r", "--format=%(objectname) %(path)", rev).splitlines():
        sha, path = line.split(" ", 1)
        entries[path] = sha
    return entries


def read_ours(ours: Path, path: str) -> str | None:
    result = subprocess.run(["git", "-C", str(ours), "show", f"{OUR_BASE}:{path}"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def load_text(reference: Path, files: dict[str, str]) -> dict[str, str]:
    """Read reference text files once, skipping binaries and large blobs."""
    cache: dict[str, str] = {}
    for path in files:
        name = path.rsplit("/", 1)[-1]
        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext in BINARY_EXT:
            continue
        target = reference / path
        try:
            size = target.stat().st_size
        except OSError:
            continue
        if ext not in TEXT_EXT and size > 200_000:
            continue
        if size > 2_000_000:
            continue
        cache[path] = target.read_text(errors="replace")
    return cache


def lines(text: str | None) -> int | None:
    return None if text is None else len(text.splitlines())


def constant(text: str, name: str) -> float | None:
    match = re.search(rf"pub const {name}: f32 = ([0-9.]+);", text)
    return float(match.group(1)) if match else None


def shadow_calls(text: str) -> dict:
    calls = re.findall(r"out\.shadow\(([^;]*)\)", text)
    literal = 0
    for call in calls:
        args = [a.strip() for a in call.split(",")]
        if len(args) >= 5 and all(re.fullmatch(r"-?[0-9.]+", a) for a in args[1:5]):
            literal += 1
    return {"total": len(calls), "all_numeric_args": literal, "interpolated": len(calls) - literal}


def module_class(path: str) -> str:
    name = Path(path).stem.lower()
    if name.endswith("-tests") or name == "tests":
        return "tests"
    if re.search(r"view|renderer|motion|typography|settings_art|weather_sky|vector|raster|font|branding|ui_sound", name):
        return "rendering"
    if re.search(r"jellyfin|plex|moonlight|player|media|music|movie|album|game|library|steam|video_catalog|aerial_video|hw_wallpaper", name):
        return "media"
    if re.search(r"smart_home|widgets|weather|phone_link|mini|stacks", name):
        return "connectivity"
    if re.search(r"platform|luna|webos|storage|update|install|companion|webhook", name):
        return "platform"
    if re.search(r"state|model|main|sdl_events|input|recents|tile|wallpaper|app-subscription|damage|egl", name):
        return "runtime"
    return "other"


def collect(reference: Path, ours: Path, tree_json: Path | None) -> dict:
    head = git(reference, "rev-parse", "HEAD").strip()
    if head != PIN:
        raise SystemExit(f"reference HEAD {head} != pinned {PIN}")

    ref_files = tree_entries(reference)
    ours_files = tree_entries(ours, OUR_BASE)
    text = load_text(reference, ref_files)

    app = json.loads((reference / "appinfo.json").read_text())
    ours_app = json.loads(read_ours(ours, "appinfo.json") or "{}")
    package = json.loads((reference / "package.json").read_text())

    common = sorted(set(ref_files) & set(ours_files))
    identical = [p for p in common if ref_files[p] == ours_files[p]]
    by_area = {}
    for area in AREAS:
        area_common = [p for p in common if p.startswith(area + "/")]
        by_area[area] = {
            "common": len(area_common),
            "identical": sum(1 for p in area_common if ref_files[p] == ours_files[p]),
            "only_reference": sum(1 for p in ref_files if p.startswith(area + "/") and p not in ours_files),
            "only_ours": sum(1 for p in ours_files if p.startswith(area + "/") and p not in ref_files),
        }

    modules = []
    for path in sorted({p for p in ref_files if p.startswith("src/") and p.endswith(".rs")} | {p for p in ours_files if p.startswith("src/") and p.endswith(".rs")}):
        ref_lines = lines(text.get(path))
        our_lines = lines(read_ours(ours, path))
        modules.append(
            {
                "path": path,
                "class": module_class(path),
                "reference_lines": ref_lines,
                "ours_lines": our_lines,
                "status": "both" if ref_lines is not None and our_lines is not None else ("only_reference" if ref_lines is not None else "only_ours"),
                "delta_lines": None if ref_lines is None or our_lines is None else ref_lines - our_lines,
            }
        )

    motion = text.get("src/motion.rs", "")
    view = text.get("src/view.rs", "")
    state = text.get("src/state.rs", "")
    diag_ref = text.get("src/diagnostics.rs", "")
    diag_ours = read_ours(ours, "src/diagnostics.rs") or ""
    renderer = text.get("src/renderer.rs", "")
    artwork = text.get("src/app_artwork.rs", "")
    development = text.get("development.md", "")

    focus_constants = {name: constant(motion, name) for name in ("FOCUS_IN", "FOCUS_OUT", "FOCUS_POP", "FOCUS_SHEEN", "SCROLL", "CARD_RISE")}
    shadow_per_file = {}
    reduced_motion = {}
    for path in sorted(p for p in ref_files if p.startswith("src/") and p.endswith(".rs")):
        source = text.get(path, "")
        stats = shadow_calls(source)
        if stats["total"]:
            shadow_per_file[path] = stats
        count = len(re.findall(r"reduced_motion", source))
        if count:
            reduced_motion[path] = count

    doc_budgets = {
        "glyph_geometry_mib": int(m.group(1)) if (m := re.search(r"(\d+) MiB/(\d+)-entry CPU cache target", development)) else None,
        "glyph_entries": int(m.group(2)) if m else None,
        "text_runs_mib": int(m2.group(1)) if (m2 := re.search(r"(\d+) MiB/(\d+)-entry GPU\s+target", development)) else None,
        "text_entries": int(m2.group(2)) if m2 else None,
        "raster_mib": int(m3.group(1)) if (m3 := re.search(r"Raster artwork has a (\d+) MiB cache budget", development)) else None,
    }
    code_budgets = {
        "glyph_geometry_bytes": int(m.group(1)) * 1024 * 1024 if (m := re.search(r"GLYPH_GEOMETRY_BUDGET: usize = (\d+) \* 1024 \* 1024", renderer)) else None,
        "glyph_entries": int(m2.group(1)) if (m2 := re.search(r"self\.glyphs\.len\(\) > (\d+)", renderer)) else None,
        "text_bytes": int(m3.group(1)) * 1024 * 1024 if (m3 := re.search(r"TEXT_GEOMETRY_BUDGET: usize = (\d+) \* 1024 \* 1024", renderer)) else None,
        "text_entries": int(m4.group(1)) if (m4 := re.search(r"self\.text_runs\.len\(\) > (\d+)", renderer)) else None,
        "raster_bytes": int(m5.group(1)) * 1024 * 1024 if (m5 := re.search(r"CACHE_BYTES: usize = (\d+) \* 1024 \* 1024", artwork)) else None,
    }
    budgets_match = all(
        [
            doc_budgets["glyph_geometry_mib"] * 1024 * 1024 == code_budgets["glyph_geometry_bytes"],
            doc_budgets["glyph_entries"] == code_budgets["glyph_entries"],
            doc_budgets["text_runs_mib"] * 1024 * 1024 == code_budgets["text_bytes"],
            doc_budgets["text_entries"] == code_budgets["text_entries"],
            doc_budgets["raster_mib"] * 1024 * 1024 == code_budgets["raster_bytes"],
        ]
    )

    def scan(patterns: dict[str, str], roots: tuple[str, ...]) -> dict[str, int]:
        found = {}
        for name, pattern in patterns.items():
            found[name] = sum(len(re.findall(pattern, body)) for path, body in text.items() if any(path.startswith(root + "/") for root in roots))
        return found

    hygiene = {
        "secret_patterns": scan(SECRET_PATTERNS, ("src", "tools", "tests", "native", "tv", "extras")),
        "drm_patterns": scan(DRM_PATTERNS, ("src", "tools", "native", "extras")),
        "netflix_mentions": sum(len(re.findall(r"(?i)netflix", body)) for path, body in text.items() if path.startswith("src/") and path.endswith(".rs")),
        "lg_header_includes": {
            "NDL_directmedia.h": sum(len(re.findall(r"#include\s*[<\"](?:NDL_directmedia|NDL_types)\.h[>\"]", body)) for path, body in text.items() if path.startswith("native/")),
            "vendored_header_present": any(Path(p).name in {"NDL_directmedia.h", "NDL_types.h"} for p in ref_files),
            "smp_api_is_own_facade": "C façade over StarfishMediaAPIs" in text.get("native/smp/vendor/smp_api.h", ""),
        },
    }

    assets = {"available": False}
    if tree_json and tree_json.is_file():
        blobs = [e for e in json.loads(tree_json.read_text())["tree"] if e["type"] == "blob"]
        by_ext: dict[str, dict[str, int]] = {}
        for entry in blobs:
            name = entry["path"].rsplit("/", 1)[-1]
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else "(none)"
            slot = by_ext.setdefault(ext, {"files": 0, "bytes": 0})
            slot["files"] += 1
            slot["bytes"] += entry.get("size", 0)
        assets = {
            "available": True,
            "total_bytes": sum(e.get("size", 0) for e in blobs),
            "blobs": len(blobs),
            "by_extension": dict(sorted(by_ext.items(), key=lambda kv: -kv[1]["bytes"])[:8]),
            "ofl_license_files": sum(1 for e in blobs if e["path"].lower().endswith("ofl.txt")),
            "font_bytes": by_ext.get("ttf", {}).get("bytes", 0),
            "image_bytes": by_ext.get("jpg", {}).get("bytes", 0),
        }

    card_w, card_h = math_model.CARD_W, math_model.CARD_H
    glow = math_model.shadow_quad(card_w - 16, card_h - 16, 90)
    grids = {
        "ours_current": math_model.grid_shadow_area(14, 1, 22, 34),
        "ours_experiment": math_model.grid_shadow_area(14, 1, 22, 42),
        "reference_home": math_model.grid_shadow_area(14, 1, 26, 40, glow),
        "reference_apps": math_model.grid_shadow_area(14, 1, 0, 40, glow),
    }
    perf = {
        "card": {"width": card_w, "height": card_h},
        "shadow_area_px": {
            "ours_resting_blur22": math_model.shadow_quad(card_w, card_h, 22),
            "ours_focused_blur34": math_model.shadow_quad(card_w, card_h, 34),
            "experiment_focused_blur42": math_model.shadow_quad(card_w, card_h, 42),
            "reference_resting_blur26": math_model.shadow_quad(card_w, card_h, 26),
            "reference_focused_blur40": math_model.shadow_quad(card_w, card_h, 40),
            "reference_halo_blur90": glow,
        },
        "ratios": {
            "experiment_over_current_focused": math_model.shadow_quad(card_w, card_h, 42) / math_model.shadow_quad(card_w, card_h, 34),
            "experiment_over_reference_full_focus": math_model.shadow_quad(card_w, card_h, 42) / (math_model.shadow_quad(card_w, card_h, 40) + glow),
            "halo_over_card_face": glow / (card_w * card_h),
        },
        "damage_px": {str(blur): math_model.damage_area(card_w, card_h, blur) for blur in (22, 34, 42)},
        "damage_delta_42_minus_34": math_model.damage_area(card_w, card_h, 42) - math_model.damage_area(card_w, card_h, 34),
        "grid_shadow_area_px": grids,
        "grid_fraction_of_1080p": {key: value / math_model.FRAME_1080P_PX for key, value in grids.items()},
        "shadow_bandwidth_gbs_60hz_readwrite": {key: math_model.bandwidth_gbs(math_model.fill_bytes(area, traffic=2), 60.0) for key, area in grids.items()},
        "full_frame": {
            "px_1080p": math_model.FRAME_1080P_PX,
            "bytes_1080p_rgba8": math_model.rgba_bytes(1920, 1080),
            "gbs_1080p_60hz": math_model.bandwidth_gbs(math_model.rgba_bytes(1920, 1080), 60.0),
            "bytes_4k_rgba8": math_model.rgba_bytes(3840, 2160),
            "bytes_4k_double_buffered": 2 * math_model.rgba_bytes(3840, 2160),
        },
        "spring": {
            "peak_k": math_model.pop_peak_k(),
            "peak": math_model.pop_peak(),
            "overshoot": math_model.pop_peak() - 1.0,
            "equivalent_damping": math_model.equivalent_damping(math_model.pop_peak() - 1.0),
            "settle_1pct_seconds": math_model.pop_settle_k() * (focus_constants["FOCUS_POP"] or 0.55),
            "zoom_at_peak": 1 + 0.07 * math_model.pop_peak(),
            "zoom_area_factor_at_peak": math_model.zoom_area_factor(1 + 0.07 * math_model.pop_peak()),
        },
        "chase": {
            "rate_per_s": math_model.chase_rate(),
            "tau_s": math_model.chase_tau(),
            "settle_96pct_s": math_model.chase_settle(0.96),
            "settle_99pct_s": math_model.chase_settle(0.99),
            "frames_96pct_at_60hz": math_model.chase_settle(0.96) * 60,
        },
        "design": {
            "ours_current": {"blur": 34, "dy": 14, "alpha": 0.4, "depth_index": math_model.depth_index(14), "softness": math_model.softness(34), "blur_over_dy": math_model.contrast(34, 14)},
            "ours_experiment": {"blur": 42, "dy": 20, "alpha": 0.5, "depth_index": math_model.depth_index(20), "softness": math_model.softness(42), "blur_over_dy": math_model.contrast(42, 20)},
            "reference_focused": {
                "blur": 40,
                "dy": 12,
                "alpha": 0.24,
                "halo_blur": 90,
                "halo_dy": 16,
                "halo_alpha": 0.3,
                "composite_alpha": math_model.composite_alpha(0.24, 0.3),
                "depth_index": math_model.depth_index(12),
                "softness": math_model.softness(40),
                "blur_over_dy": math_model.contrast(40, 12),
            },
        },
    }

    facts = {
        "schema": 1,
        "generated_by": "research/scripts/compare_reference_launcher.py",
        "labels": {
            "blob_and_line_counts": "OBSERVED (git, pinned trees)",
            "constants": "OBSERVED (source literals)",
            "perf_math": "MODEL (closed form from source constants; no GPU, TV or clock measurement)",
            "native_runs": "NOT_RUN",
        },
        "reference": {
            "full_name": REFERENCE,
            "commit": head,
            "commit_count": 5,
            "commit_count_source": "GitHub commits API rel=last (one commit per page)",
            "commits_signed": False,
            "history": "single import plus four edits; no incremental feature history",
            "license": (text.get("license") or "").splitlines()[0] if text.get("license") else None,
            "app_id": app.get("id"),
            "app_version": app.get("version"),
            "package_version": package.get("version"),
            "tag": "v2.2.160",
            "files_total": len(ref_files),
            "rust_files": sum(1 for p in ref_files if p.endswith(".rs")),
            "rust_lines": sum(lines(text.get(p)) or 0 for p in ref_files if p.endswith(".rs")),
            "workflows": sorted(p for p in ref_files if p.startswith(".github/workflows/")),
        },
        "ours": {
            "base": OUR_BASE,
            "compared_rev": OUR_BASE,
            "app_id": ours_app.get("id"),
            "app_version": ours_app.get("version"),
            "files_total": len(ours_files),
            "rust_files": sum(1 for p in ours_files if p.endswith(".rs")),
            "fork_of": "ecklf/lg-luma",
            "shares_history_with_reference": False,
        },
        "blobs": {
            "common_paths": len(common),
            "identical": len(identical),
            "changed": len(common) - len(identical),
            "only_reference": len(set(ref_files) - set(ours_files)),
            "only_ours": len(set(ours_files) - set(ref_files)),
            "by_area": by_area,
            "identical_root_files": [p for p in identical if "/" not in p],
        },
        "components": modules,
        "focus": {
            "constants": focus_constants,
            "shadow_calls": {
                "total": sum(v["total"] for v in shadow_per_file.values()),
                "files": len(shadow_per_file),
                "all_numeric_args": sum(v["all_numeric_args"] for v in shadow_per_file.values()),
                "interpolated": sum(v["interpolated"] for v in shadow_per_file.values()),
                "per_file": shadow_per_file,
            },
            "reduced_motion_sites": reduced_motion,
            "reduced_motion_total": sum(reduced_motion.values()),
            "apps_resting_skips_shadow": bool(re.search(r"if state\.page != Page::Apps \|\| level > 0\.", view)),
            "apps_resting_skip_condition": "state.page != Page::Apps || level > 0.",
            "independent_of_our_experiment": not any("LUMA_FOCUS_DEPTH" in body or "focus_experiment" in body for path, body in text.items() if path.endswith(".rs")),
            "zoom": "1 + 0.07 * focus_pop, disabled when reduced_motion",
        },
        "diagnostics": {
            "reference_fields": sorted(set(re.findall(r"pub (\w+):", diag_ref))),
            "ours_fields": sorted(set(re.findall(r"pub (\w+):", diag_ours))),
            "ours_superset": set(re.findall(r"pub (\w+):", diag_ref)) <= set(re.findall(r"pub (\w+):", diag_ours)),
            "reference_has_timeline": "timeline" in diag_ref,
            "ours_has_timeline": "timeline" in diag_ours,
        },
        "budgets": {"docs": doc_budgets, "code": code_budgets, "match": budgets_match},
        "hygiene": hygiene,
        "assets": assets,
        "perf_math": perf,
        "gates": {
            "reference_clone": "OBSERVED",
            "native_build": "BLOCKED (no toolchain in this environment)",
            "rendering": "NOT_RUN",
            "frame_pacing": "NOT_RUN",
            "physical_tv": "NOT_RUN (out of scope, no device contact)",
            "visual_difference": "NOT_RUN",
        },
    }
    return facts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=Path("/home/user/luma-ref/luma-webos-launcher"))
    parser.add_argument("--ours", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--tree-json", type=Path, default=Path("/home/user/luma-ref/tree.json"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    if not (args.reference / ".git").exists():
        print(f"reference clone missing: {args.reference}", file=sys.stderr)
        return 2
    try:
        facts = collect(args.reference, args.ours, args.tree_json)
    except SystemExit as error:
        print(error, file=sys.stderr)
        return 2

    out = args.out or (args.ours / "research/audit/reference-launcher-facts.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "out": str(out),
                "reference_commit": facts["reference"]["commit"],
                "files": facts["reference"]["files_total"],
                "identical_blobs": facts["blobs"]["identical"],
                "modules_only_reference": sum(1 for m in facts["components"] if m["status"] == "only_reference"),
                "modules_only_ours": sum(1 for m in facts["components"] if m["status"] == "only_ours"),
                "budgets_match": facts["budgets"]["match"],
                "experiment_area_ratio": round(facts["perf_math"]["ratios"]["experiment_over_current_focused"], 4),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
