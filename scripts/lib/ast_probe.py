"""
scripts/lib/ast_probe.py — Zero-import AST Pre-Flight + Ochiai fault localization.

Parses test files with ast.parse (executes ZERO imports) and uses
importlib.util.find_spec() to check module availability without loading.
Collapses thousands of collection errors into an Ochiai root-cause table.
"""
from __future__ import annotations

import ast
import importlib.util
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__",
    ".agent-kb", ".mypy_cache", ".pytest_cache", "target", "vendor",
}


def iter_py_files(root: Path):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for f in sorted(files):
            if f.endswith(".py"):
                yield Path(dirpath, f)


def build_local_module_index(root: Path) -> tuple[set[str], dict[str, Path]]:
    local_roots: set[str] = set()
    dotted_map: dict[str, Path] = {}
    for p in iter_py_files(root):
        rel = p.relative_to(root)
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            local_roots.add(parts[0])
            dotted_map[".".join(parts)] = p
            if parts[0] in ("src", "lib", "python", "packages") and len(parts) > 1:
                local_roots.add(parts[1])
                dotted_map[".".join(parts[1:])] = p
    return local_roots, dotted_map


def is_pkg_installed(pkg: str, stdlib: set[str], local_roots: set[str],
                     cache: dict[str, bool]) -> bool:
    if pkg in stdlib or pkg in local_roots or pkg.startswith("_"):
        return True
    if pkg not in cache:
        try:
            cache[pkg] = importlib.util.find_spec(pkg) is not None
        except Exception:
            cache[pkg] = False
    return cache[pkg]


def triage_test_suite(path: str | Path = "."):
    """Zero-import triage. Returns (report_dict, elapsed_ms)."""
    import time
    t0 = time.perf_counter()
    root = Path(path).resolve()
    local_roots, _ = build_local_module_index(root)
    stdlib = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()
    cache: dict[str, bool] = {}

    test_files = [
        p for p in iter_py_files(root)
        if p.name.startswith("test_") or p.name.endswith("_test.py")
    ]

    runnable: list[str] = []
    blocked: list[dict] = []
    syntax_errors: list[dict] = []
    dep_to_failed: dict[str, set] = defaultdict(set)
    dep_to_passed: dict[str, set] = defaultdict(set)

    for tf in test_files:
        rel = str(tf.relative_to(root))
        try:
            tree = ast.parse(tf.read_text(encoding="utf-8", errors="replace"), filename=rel)
        except SyntaxError as e:
            syntax_errors.append({"file": rel, "error": f"L{e.lineno}: {e.msg}"})
            continue

        imports_used: set[str] = set()
        missing_deps: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    rp = alias.name.split(".")[0]
                    imports_used.add(rp)
                    if not is_pkg_installed(rp, stdlib, local_roots, cache):
                        missing_deps.add(rp)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                rp = node.module.split(".")[0]
                imports_used.add(rp)
                if not is_pkg_installed(rp, stdlib, local_roots, cache):
                    missing_deps.add(rp)

        if missing_deps:
            blocked.append({"file": rel, "missing": sorted(missing_deps)})
            for d in imports_used:
                dep_to_failed[d].add(rel)
        else:
            runnable.append(rel)
            for d in imports_used:
                dep_to_passed[d].add(rel)

    total_failed = len(blocked)
    ochiai: list[dict] = []
    if total_failed > 0:
        for dep, fset in dep_to_failed.items():
            ef = len(fset)
            ep = len(dep_to_passed.get(dep, set()))
            denom = math.sqrt(total_failed * (ef + ep))
            score = round(ef / denom, 4) if denom > 0 else 0.0
            installed = is_pkg_installed(dep, stdlib, local_roots, cache)
            if not installed or score >= 0.25:
                ochiai.append({
                    "module": dep,
                    "installed": installed,
                    "blocked_tests": ef,
                    "runnable_tests": ep,
                    "ochiai_score": score,
                })
        ochiai.sort(key=lambda x: (-x["ochiai_score"], -x["blocked_tests"]))

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "scan_duration_ms": elapsed_ms,
        "total_test_files": len(test_files),
        "runnable_now": len(runnable),
        "blocked_at_collection": len(blocked),
        "syntax_errors": len(syntax_errors),
        "ochiai_root_cause_blockers": ochiai[:15],
        "sample_runnable": runnable[:15],
        "sample_blocked": blocked[:10],
        "sample_syntax_errors": syntax_errors[:5],
    }, elapsed_ms
