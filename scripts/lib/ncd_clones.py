"""
scripts/lib/ncd_clones.py — Kolmogorov Normalized Compression Distance (NCD)
semantic clone hunter. Zero LLM, pure zlib+AST, ~<1s on typical repos.

Uses alpha-normalized AST dumps so variable renames don't defeat detection.
NCD(x,y) = (Z(xy) - min(Z(x),Z(y))) / max(Z(x),Z(y))  ∈ [0,1]
"""
from __future__ import annotations

import ast
import hashlib
import os
import zlib
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


def _alpha_normalize_source(src: str) -> str:
    """Very light alpha-renaming: replace identifiers with canonical Vn slots."""
    import ast
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src
    var_map: dict[str, str] = {}

    class Norm(ast.NodeTransformer):
        def _n(self, name: str) -> str:
            if name not in var_map:
                var_map[name] = f"V{len(var_map)}"
            return var_map[name]

        def visit_Name(self, node):
            if isinstance(node.ctx, (ast.Store, ast.Param)):
                return ast.Name(id=self._n(node.id), ctx=node.ctx)
            return ast.Name(id=var_map.get(node.id, node.id), ctx=node.ctx)

        def visit_arg(self, node):
            return ast.arg(arg=self._n(node.arg), annotation=None)

    tree = Norm().visit(tree)
    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree)
    except Exception:
        return ast.dump(tree, include_attributes=False)


def extract_symbols(root: Path, min_loc: int = 12):
    records = []
    for p in iter_py_files(root):
        rel = str(p.relative_to(root))
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
            tree = ast_parse_safe(src)
        except Exception:
            continue
        if tree is None:
            continue
        for node in getattr(tree, "body", []):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            start = node.lineno
            end = getattr(node, "end_lineno", start)
            loc = max(1, end - start + 1)
            if loc < min_loc:
                continue
            norm_src = _alpha_normalize_source(ast_unparse(node))
            norm_bytes = norm_src.encode("utf-8")
            comp = len(zlib.compress(norm_bytes, 6))
            records.append({
                "qualname": f"{rel}::{node.name}",
                "file": rel,
                "symbol": node.name,
                "lineno": start,
                "loc": loc,
                "norm_bytes": norm_bytes,
                "comp_len": comp,
            })
    return records


def ast_parse_safe(src: str):
    import ast
    try:
        return ast.parse(src)
    except SyntaxError:
        return None


def ast_unparse(node):
    import ast
    try:
        return ast.unparse(node)
    except Exception:
        return ast.dump(node, include_attributes=False)


def find_clones(root: Path, min_loc: int = 12, threshold: float = 0.22):
    """Find semantic clones via NCD. Returns sorted list + metadata."""
    import time
    t0 = time.perf_counter()
    recs = [r for r in extract_symbols(root, min_loc) if r["loc"] >= min_loc]
    recs.sort(key=lambda x: x["comp_len"])
    n = len(recs)
    clones = []

    for i in range(n):
        r1 = recs[i]
        for j in range(i + 1, n):
            r2 = recs[j]
            if r2["comp_len"] > r1["comp_len"] * 1.45:
                break
            if r1["file"] == r2["file"] and r1["symbol"] == r2["symbol"]:
                continue
            combined = r1["norm_bytes"] + b"\n" + r2["norm_bytes"]
            c_xy = len(zlib.compress(combined, 6))
            ncd = (c_xy - min(r1["comp_len"], r2["comp_len"])) / max(r1["comp_len"], r2["comp_len"])
            if ncd <= threshold:
                clones.append({
                    "a": f"{r1['file']}:L{r1['lineno']} ({r1['symbol']})",
                    "b": f"{r2['file']}:L{r2['lineno']} ({r2['symbol']})",
                    "ncd": round(ncd, 4),
                    "loc_a": r1["loc"],
                    "loc_b": r2["loc"],
                })

    clones.sort(key=lambda x: x["ncd"])
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "scan_duration_ms": elapsed_ms,
        "functions_compared": n,
        "threshold": threshold,
        "min_loc": min_loc,
        "clones_found": len(clones),
        "clones": clones[:30],
    }
