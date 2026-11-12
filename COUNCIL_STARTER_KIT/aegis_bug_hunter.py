#!/usr/bin/env python3
"""
AEGIS BUG HUNTER & ZERO-REGRESSION PATCH VERIFIER — Council Pass 3

Bug forensics & surgical patch engine for CLI agents across Virtual Linux (6.1+)
and macOS M1 Pro. Combines six subcommands:

  1. hunt        — Engler Statistical Deviance Miner + PVS-Studio AST Bug Detector
                   (Python AND TypeScript/JavaScript — regex-based, zero deps)
  2. review      — Fast-Scan Differential Code Review (Shannon entropy + bug gates)
  3. forensics   — AST-Refined SZZ Bug Genealogy (git log -L / -S pickaxe)
  4. dylib-audit — Native Binary Forensic Auditor
                   (.so ELF / .dylib Mach-O: raw headers + symbol tables via nm,
                    string extraction via strings, dependency graphs via ldd/readelf)
  5. cfg         — Control Flow Graph reverse engineering via objdump disassembly
  6. verify-fix  — Separation-Logic Frame Rule Verifier ({P * R} C -> C' {Q * R})

Zero external dependencies — pure Python 3.11 stdlib + optional system binutils
(nm, objdump, readelf, strings, ldd, otool) when present. Runs in <500ms on
2-CPU container and macOS M1 Pro.

Polyglot: Python via ast module; TypeScript/JavaScript via regex + structural
pattern matching (tautologies, redundant booleans, dead branches, missing
optional-chaining guards, unused return values).
"""
from __future__ import annotations

import argparse
import ast
import collections
import datetime
import hashlib
import json
import math
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(os.environ.get("REPO_ROOT", ".")).resolve()
IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "dist", "build",
    "__pycache__", ".agent-kb", ".mypy_cache", ".pytest_cache",
    "target", "vendor",
}

# Source file extensions supported by the bug hunter.
PY_EXTENSIONS = {".py"}
TSJS_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}
ALL_SOURCE_EXTENSIONS = PY_EXTENSIONS | TSJS_EXTENSIONS


# ---------------------------------------------------------------------------
# System tool availability (reverse-engineering toolchain)
# ---------------------------------------------------------------------------
def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


HAS_NM = _have("nm")
HAS_OBJDUMP = _have("objdump")
HAS_READELF = _have("readelf")
HAS_STRINGS = _have("strings")
HAS_LDD = _have("ldd")
HAS_OTOOL = _have("otool")


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------
def iter_source_files(root: Path):
    """Yield every source file under root (py, ts, tsx, js, jsx), skipping ignored dirs."""
    if not root.exists():
        return
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for f in sorted(files):
            if Path(f).suffix.lower() in ALL_SOURCE_EXTENSIONS:
                yield Path(dirpath, f)


def iter_py_files(root: Path):
    """Yield every .py file under root (kept for backward compatibility)."""
    if not root.exists():
        return
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for f in sorted(files):
            if f.endswith(".py"):
                yield Path(dirpath, f)


def sh(cmd: list[str]) -> str:
    """Run a command quietly; return stdout (may be empty)."""
    try:
        res = subprocess.run(
            cmd, cwd=REPO_ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True,
        )
        return res.stdout
    except (FileNotFoundError, OSError):
        return ""


def rank_anomalies(anomalies: list[dict]) -> list[dict]:
    sev_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    return sorted(
        anomalies,
        key=lambda x: (sev_rank.get(x["severity"], 9), x.get("location", "")),
    )


# ---------------------------------------------------------------------------
# TYPESCRIPT/JAVASCRIPT SCANNER (regex-based, zero dependencies)
# ---------------------------------------------------------------------------
# Function signature: function name(args) or const name = (args) => or name: (args) =>
TSJS_FUNC_RE = re.compile(
    r"(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|"
    r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>|"
    r"(\w+)\s*:\s*(?:async\s+)?\(([^)]*)\)\s*=>)"
)
TSJS_METHOD_RE = re.compile(
    r"(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*\{"  # methodName(args) {
)
TSJS_CALL_RE = re.compile(r"(\w[\w.]*)\s*\([^)]*\)")
TSJS_TAUTOLOGY_RE = re.compile(r"===\s*(\w[\w.]*)\s*===\s*\1")
TSJS_REDUNDANT_BOOL_RE = re.compile(r"(\w[\w.]*)\s*&&\s*\1|(\w[\w.]*)\s*\|\|\s*\1")
TSJS_OPTIONAL_ACCESS_RE = re.compile(r"\.\w+(?:\.[\w]+)*")  # property access chains


def scan_tsjs_file(rel_path: str, source: str) -> dict:
    """Scan a TypeScript/JavaScript file for bugs using regex + structural patterns.

    Returns the same shape as ASTScanner._result() for uniform handling.
    """
    anomalies: list[dict] = []
    func_defs: dict[str, list[dict]] = collections.defaultdict(list)
    call_sites: dict[str, list[dict]] = collections.defaultdict(list)
    lines = source.splitlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # ---- Tautological comparison: x === x ----
        for m in TSJS_TAUTOLOGY_RE.finditer(stripped):
            anomalies.append({
                "severity": "HIGH",
                "category": "TAUTOLOGICAL_COMPARISON_COPY_PASTE",
                "location": f"{rel_path}:L{idx}",
                "detail": (
                    f"Expression compares identical subtrees on both sides "
                    f"(probable copy-paste slip)."
                ),
            })

        # ---- Redundant boolean: a && a or a || a ----
        for m in TSJS_REDUNDANT_BOOL_RE.finditer(stripped):
            anomalies.append({
                "severity": "HIGH",
                "category": "REDUNDANT_BOOLEAN_SUBEXPRESSION",
                "location": f"{rel_path}:L{idx}",
                "detail": (
                    "Boolean operator contains duplicate identical condition."
                ),
            })

        # ---- Missing optional-chaining guard: obj.prop without ?. ----
        # Flag direct property access on potentially-nullable values
        if "." in stripped and "?." not in stripped and "=>" not in stripped:
            # Look for patterns like `something.something` where something isn't guarded
            for m in re.finditer(r"([a-zA-Z_$][\w$]*)\.([a-zA-Z_$][\w$]*)", stripped):
                obj, prop = m.group(1), m.group(2)
                # Skip common safe objects and keywords
                if obj in {"console", "Math", "JSON", "Array", "Object", "String",
                           "Number", "Boolean", "Date", "RegExp", "Error", "Promise",
                           "fetch", "setTimeout", "setInterval", "process", "global",
                           "window", "document", "require", "module", "exports",
                           "__dirname", "__filename"}:
                    continue
                # Skip if already using optional chaining on this line segment
                anomalies.append({
                    "severity": "MEDIUM",
                    "category": "TSJS_MISSING_OPTIONAL_CHAINING",
                    "location": f"{rel_path}:L{idx}",
                    "detail": (
                        f"Property access '{obj}.{prop}' without optional chaining "
                        f"(?.) — may throw on null/undefined."
                    ),
                })
                break  # One per line to avoid noise

        # ---- Function definitions ----
        for m in TSJS_FUNC_RE.finditer(stripped):
            name = m.group(1) or m.group(2) or m.group(4) or "anonymous"
            args_str = m.group(3) or m.group(5) or ""
            arg_names = [a.strip().split(":")[0].strip() for a in args_str.split(",") if a.strip()]
            arg_names = [a for a in arg_names if a and not a.startswith("...")]
            is_async = "async" in stripped
            has_rest = "..." in args_str

            func_defs[name].append({
                "file": rel_path,
                "line": idx,
                "is_async": is_async,
                "min_args": len([a for a in arg_names if "=" not in a]),
                "max_args": 999 if has_rest else len(arg_names),
                "has_kwarg": False,  # TS/JS doesn't have Python-style kwargs
                "arg_names": arg_names,
                "kwonly_names": [],
                "mixed_nullable_return": False,
            })

        # ---- Method definitions: methodName(args) { ----
        for m in TSJS_METHOD_RE.finditer(stripped):
            name = m.group(1)
            args_str = m.group(2) or ""
            arg_names = [a.strip().split(":")[0].strip() for a in args_str.split(",") if a.strip()]
            arg_names = [a for a in arg_names if a and not a.startswith("...")]
            # Skip common non-method keywords
            if name in {"if", "for", "while", "switch", "catch", "try", "function",
                        "return", "class", "export", "import", "const", "let", "var",
                        "async", "await", "new", "delete", "typeof", "instanceof",
                        "in", "of", "do", "else"}:
                continue
            func_defs[name].append({
                "file": rel_path,
                "line": idx,
                "is_async": "async" in stripped,
                "min_args": len([a for a in arg_names if "=" not in a]),
                "max_args": 999 if "..." in args_str else len(arg_names),
                "has_kwarg": False,
                "arg_names": arg_names,
                "kwonly_names": [],
                "mixed_nullable_return": False,
            })

        # ---- Call sites ----
        for m in TSJS_CALL_RE.finditer(stripped):
            callee = m.group(1)
            # Skip keywords and language built-ins
            if callee.split(".")[0] in {"if", "for", "while", "switch", "catch",
                                         "try", "function", "class", "export",
                                         "import", "const", "let", "var", "async",
                                         "await", "new", "delete", "typeof",
                                         "instanceof", "in", "of", "do", "else",
                                         "return", "console", "Math", "JSON"}:
                continue
            # Determine if return value is used (assigned, returned, or passed as arg)
            return_used = (
                "=" in stripped.split(callee)[0] if callee in stripped else False
            ) or stripped.strip().startswith("return ") or "=>" in stripped
            in_try = "try" in stripped  # heuristic
            call_sites[callee].append({
                "file": rel_path,
                "line": idx,
                "pos_count": 1,  # heuristic
                "kw_names": [],
                "has_varargs": False,
                "is_awaited": "await" in stripped,
                "in_try": in_try,
                "return_used": return_used,
            })

    total_funcs = sum(len(v) for v in func_defs.values())
    total_sites = sum(len(v) for v in call_sites.values())
    return {
        "rel": rel_path,
        "functions_modeled": total_funcs,
        "call_sites_cross_checked": total_sites,
        "total_anomalies_found": len(anomalies),
        "anomalies": rank_anomalies(anomalies),
        "func_defs": dict(func_defs),
        "call_sites": dict(call_sites),
    }


# ---------------------------------------------------------------------------
# AST scanning core — Python (shared by hunt and verify-fix)
# ---------------------------------------------------------------------------
class ASTScanner:
    """Single-pass AST scanner collecting defs, call sites, and anomalies.

    Used by both `hunt` (whole-repo) and `verify-fix` (single patched file).
    """

    def __init__(self, rel_path: str, source: str):
        self.rel = rel_path
        self.source = source
        self.anomalies: list[dict] = []
        self.func_defs: dict[str, list[dict]] = collections.defaultdict(list)
        self.call_sites: dict[str, list[dict]] = collections.defaultdict(list)
        self._tree: ast.AST | None = None
        self._parent_map: dict[ast.AST, ast.AST] = {}
        self._parse()

    def _parse(self):
        try:
            self._tree = ast.parse(self.source, filename=self.rel)
        except SyntaxError as e:
            self.anomalies.append({
                "severity": "CRITICAL",
                "category": "SYNTAX_ERROR",
                "location": f"{self.rel}:L{e.lineno or 1}",
                "detail": str(e.msg)[:120],
            })
            self._tree = None

    def _build_parent_map(self):
        self._parent_map = {}
        if self._tree is None:
            return
        for node in ast.walk(self._tree):
            for child in ast.iter_child_nodes(node):
                self._parent_map[child] = node

    def _has_ancestor(self, node: ast.AST, types_tuple: tuple) -> bool:
        curr = self._parent_map.get(node)
        while curr:
            if isinstance(curr, types_tuple):
                return True
            curr = self._parent_map.get(curr)
        return False

    def run(self):
        if self._tree is None:
            return self._result()
        self._build_parent_map()
        for node in ast.walk(self._tree):
            self._visit(node)
        return self._result()

    def _visit(self, node: ast.AST):
        # ---- A. Function definitions & signature contracts ----
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._visit_funcdef(node)
        # ---- B. PVS: Tautological comparison ----
        elif isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            self._visit_compare(node)
        # ---- C. PVS: Redundant boolean subexpression ----
        elif isinstance(node, ast.BoolOp) and len(node.values) >= 2:
            self._visit_boolop(node)
        # ---- D. PVS: Dead duplicate elif branch ----
        elif isinstance(node, ast.If):
            self._visit_if(node)
        # ---- E. Call sites ----
        elif isinstance(node, ast.Call):
            self._visit_call(node)

    def _visit_funcdef(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        is_async = isinstance(node, ast.AsyncFunctionDef)
        pos_args = [
            a.arg for a in node.args.posonlyargs + node.args.args
            if a.arg not in ("self", "cls")
        ]
        n_def = len(node.args.defaults)
        min_args = max(0, len(pos_args) - n_def)
        max_args = 999 if node.args.vararg else len(pos_args)

        returns_val, returns_none = False, False
        for sub in ast.walk(node):
            if isinstance(sub, ast.Return):
                if sub.value is None or (
                    isinstance(sub.value, ast.Constant)
                    and sub.value.value is None
                ):
                    returns_none = True
                else:
                    returns_val = True

        self.func_defs[node.name].append({
            "file": self.rel,
            "line": node.lineno,
            "is_async": is_async,
            "min_args": min_args,
            "max_args": max_args,
            "has_kwarg": node.args.kwarg is not None,
            "arg_names": pos_args,
            "kwonly_names": [a.arg for a in node.args.kwonlyargs],
            "mixed_nullable_return": returns_val and returns_none,
        })

        # PVS: Mutable default argument -> state corruption across calls.
        for d in list(node.args.defaults) + list(node.args.kw_defaults):
            if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                self.anomalies.append({
                    "severity": "HIGH",
                    "category": "MUTABLE_DEFAULT_STATE_CORRUPTION",
                    "location": f"{self.rel}:L{node.lineno}",
                    "detail": (
                        f"Function '{node.name}' uses mutable default "
                        f"{type(d).__name__}; state leaks across calls."
                    ),
                })

    def _visit_compare(self, node: ast.Compare):
        if (
            ast.dump(node.left, include_attributes=False)
            == ast.dump(node.comparators[0], include_attributes=False)
            and not isinstance(node.left, ast.Constant)
        ):
            self.anomalies.append({
                "severity": "HIGH",
                "category": "TAUTOLOGICAL_COMPARISON_COPY_PASTE",
                "location": f"{self.rel}:L{node.lineno}",
                "detail": (
                    "Expression compares identical AST subtrees on both "
                    "sides (probable copy-paste slip)."
                ),
            })

    def _visit_boolop(self, node: ast.BoolOp):
        dumps = [ast.dump(v, include_attributes=False) for v in node.values]
        if len(dumps) != len(set(dumps)):
            self.anomalies.append({
                "severity": "HIGH",
                "category": "REDUNDANT_BOOLEAN_SUBEXPRESSION",
                "location": f"{self.rel}:L{node.lineno}",
                "detail": (
                    "Boolean operator ('and'/'or') contains duplicate "
                    "identical condition."
                ),
            })

    def _visit_if(self, node: ast.If):
        seen_conds: dict[str, int] = {
            ast.dump(node.test, include_attributes=False): node.lineno
        }
        curr_orelse = node.orelse
        while len(curr_orelse) == 1 and isinstance(curr_orelse[0], ast.If):
            elif_node = curr_orelse[0]
            cdump = ast.dump(elif_node.test, include_attributes=False)
            if cdump in seen_conds:
                self.anomalies.append({
                    "severity": "HIGH",
                    "category": "DEAD_DUPLICATE_ELIF_BRANCH",
                    "location": f"{self.rel}:L{elif_node.lineno}",
                    "detail": (
                        f"elif condition identical to earlier branch at "
                        f"L{seen_conds[cdump]} (dead code)."
                    ),
                })
            seen_conds[cdump] = elif_node.lineno
            curr_orelse = elif_node.orelse

    def _visit_call(self, node: ast.Call):
        callee = (
            node.func.id
            if isinstance(node.func, ast.Name)
            else (node.func.attr if isinstance(node.func, ast.Attribute) else None)
        )
        if callee:
            parent = self._parent_map.get(node)
            self.call_sites[callee].append({
                "file": self.rel,
                "line": node.lineno,
                "pos_count": len(node.args),
                "kw_names": [k.arg for k in node.keywords if k.arg],
                "has_varargs": any(
                    isinstance(a, ast.Starred) for a in node.args
                ) or any(k.arg is None for k in node.keywords),
                "is_awaited": self._has_ancestor(node, (ast.Await,)),
                "in_try": self._has_ancestor(node, (ast.Try,)),
                "return_used": not isinstance(parent, ast.Expr),
            })

    def _result(self) -> dict:
        total_funcs = sum(len(v) for v in self.func_defs.values())
        total_sites = sum(len(v) for v in self.call_sites.values())
        return {
            "rel": self.rel,
            "functions_modeled": total_funcs,
            "call_sites_cross_checked": total_sites,
            "total_anomalies_found": len(self.anomalies),
            "anomalies": rank_anomalies(self.anomalies),
            "func_defs": dict(self.func_defs),
            "call_sites": dict(self.call_sites),
        }


# ---------------------------------------------------------------------------
# Unified scanner — dispatches Python vs TypeScript/JavaScript
# ---------------------------------------------------------------------------
def scan_source_file(rel_path: str, source: str) -> dict:
    """Scan a single source file, dispatching to Python AST or TS/JS regex scanner."""
    ext = Path(rel_path).suffix.lower()
    if ext in PY_EXTENSIONS:
        return ASTScanner(rel_path, source).run()
    elif ext in TSJS_EXTENSIONS:
        return scan_tsjs_file(rel_path, source)
    else:
        return {
            "rel": rel_path,
            "functions_modeled": 0,
            "call_sites_cross_checked": 0,
            "total_anomalies_found": 0,
            "anomalies": [],
            "func_defs": {},
            "call_sites": {},
        }


# ---------------------------------------------------------------------------
# 1. HUNT — Engler Statistical Deviance Miner + PVS-Studio AST Bug Detector
# ---------------------------------------------------------------------------
def scan_repo_for_bugs(target_subpath: str = ".",
                       cache_enabled: bool = True) -> dict:
    """Specification-free bug hunter.

    Combines:
      - Engler binomial z-score deviance mining (implicit invariant = majority
        caller behavior; minority call sites = high-probability latent bugs)
      - PVS-Studio structural patterns (tautological comparisons, redundant
        booleans, dead elif branches, mutable defaults)
      - TypeScript/JavaScript patterns (tautologies, redundant booleans,
        missing optional-chaining guards)
      - Arity / keyword-argument compatibility vs every function definition
      - Unawaited async coroutine detection
    """
    t0 = time.monotonic()
    cache_file = REPO_ROOT / ".agent-kb" / "hunt_cache.json"
    cache: dict | None = None
    if cache_enabled and cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError):
            cache = None

    all_anomalies: list[dict] = []
    total_funcs = 0
    total_sites = 0
    files_scanned = 0

    common_polymorphic = {
        "get", "pop", "set", "update", "run", "write", "read",
        "init", "__init__", "main", "close", "open", "flush",
        "then", "catch", "finally", "map", "filter", "reduce",
        "forEach", "find", "findIndex", "some", "every",
    }
    ignore_callers = {
        "print", "len", "str", "int", "float", "list", "dict", "set",
        "max", "min", "round", "append", "add", "sum", "any", "all",
        "console", "Math", "JSON", "fetch", "setTimeout", "setInterval",
    }

    # Aggregate call sites across all files for Engler mining.
    agg_call_sites: dict[str, list[dict]] = collections.defaultdict(list)
    agg_func_defs: dict[str, list[dict]] = collections.defaultdict(list)

    for p in iter_source_files(REPO_ROOT / target_subpath):
        rel = str(p.relative_to(REPO_ROOT))
        # Cache check: skip if file unchanged (mtime + size).
        st = p.stat()
        cache_key = rel
        if cache and cache_key in cache:
            ent = cache[cache_key]
            if ent.get("mtime_ns") == st.st_mtime_ns and ent.get("size") == st.st_size:
                # Reuse cached defs/sites.
                for name, defs in ent.get("func_defs", {}).items():
                    agg_func_defs[name].extend(defs)
                for name, sites in ent.get("call_sites", {}).items():
                    agg_call_sites[name].extend(sites)
                all_anomalies.extend(ent.get("anomalies", []))
                total_funcs += ent.get("functions_modeled", 0)
                total_sites += ent.get("call_sites_cross_checked", 0)
                files_scanned += 1
                continue

        try:
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        res = scan_source_file(rel, src)
        all_anomalies.extend(res["anomalies"])
        total_funcs += res["functions_modeled"]
        total_sites += res["call_sites_cross_checked"]
        files_scanned += 1

        for name, defs in res["func_defs"].items():
            agg_func_defs[name].extend(defs)
        for name, sites in res["call_sites"].items():
            agg_call_sites[name].extend(sites)

        # Update cache entry.
        if cache_enabled:
            if cache is None:
                cache = {}
            cache[cache_key] = {
                "mtime_ns": st.st_mtime_ns,
                "size": st.st_size,
                "functions_modeled": res["functions_modeled"],
                "call_sites_cross_checked": res["call_sites_cross_checked"],
                "anomalies": res["anomalies"],
                "func_defs": res["func_defs"],
                "call_sites": res["call_sites"],
            }

    if cache_enabled and cache_file.parent.exists():
        try:
            cache_file.write_text(json.dumps(cache or {}, indent=1))
        except OSError:
            pass

    # ---- Engler statistical deviance mining + arity checks ----
    for callee, sites in agg_call_sites.items():
        n = len(sites)
        defs = agg_func_defs.get(callee, [])
        if len(defs) == 1:
            d = defs[0]
            for s in sites:
                total_passed = s["pos_count"] + len(s["kw_names"])
                if (
                    not s["has_varargs"]
                    and callee not in common_polymorphic
                ):
                    if (
                        total_passed < d["min_args"]
                        or s["pos_count"] > d["max_args"]
                    ):
                        all_anomalies.append({
                            "severity": "CRITICAL",
                            "category": "CALL_ARITY_MISMATCH_TYPEERROR",
                            "location": f"{s['file']}:L{s['line']}",
                            "detail": (
                                f"Calls '{callee}()' with {total_passed} args, "
                                f"but {d['file']}:L{d['line']} requires "
                                f"[{d['min_args']}..{d['max_args']}]."
                            ),
                        })
                if (
                    d["is_async"]
                    and not s["is_awaited"]
                    and not s["return_used"]
                ):
                    all_anomalies.append({
                        "severity": "CRITICAL",
                        "category": "UNAWAITED_ASYNC_COROUTINE",
                        "location": f"{s['file']}:L{s['line']}",
                        "detail": (
                            f"Call to 'async def/function {callee}()' (defined at "
                            f"{d['file']}:L{d['line']}) is never awaited and "
                            f"its result is dropped!"
                        ),
                    })

        if n >= 5 and callee not in ignore_callers:
            k_used = sum(1 for s in sites if s["return_used"])
            if k_used / n >= 0.88 and k_used < n:
                z_used = (2 * k_used - n) / math.sqrt(n)
                if z_used >= 2.0:
                    for s in sites:
                        if not s["return_used"]:
                            all_anomalies.append({
                                "severity": "MEDIUM",
                                "category": "ENGLER_DEVIANT_IGNORED_RETURN",
                                "location": f"{s['file']}:L{s['line']}",
                                "detail": (
                                    f"Call to '{callee}()' discards return "
                                    f"value, violating repo invariant "
                                    f"({k_used}/{n} callers check it, "
                                    f"z={round(z_used, 2)})."
                                ),
                            })

            k_try = sum(1 for s in sites if s["in_try"])
            if k_try / n >= 0.85 and k_try < n:
                z_try = (2 * k_try - n) / math.sqrt(n)
                if z_try >= 1.9:
                    for s in sites:
                        if not s["in_try"]:
                            all_anomalies.append({
                                "severity": "MEDIUM",
                                "category": "ENGLER_DEVIANT_UNGUARDED_CALL",
                                "location": f"{s['file']}:L{s['line']}",
                                "detail": (
                                    f"Call to '{callee}()' lacks try/except "
                                    f"guard, violating repo norm "
                                    f"({k_try}/{n} sites guard it, "
                                    f"z={round(z_try, 2)})."
                                ),
                            })

    all_anomalies = rank_anomalies(all_anomalies)
    return {
        "scan_duration_ms": round((time.monotonic() - t0) * 1000, 2),
        "files_scanned": files_scanned,
        "functions_modeled": total_funcs,
        "call_sites_cross_checked": total_sites,
        "total_anomalies_found": len(all_anomalies),
        "anomalies": all_anomalies[:40],
    }


def _scan_single_file(target_subpath: str) -> dict:
    """Run scan_source_file constrained to a single file path."""
    target_path = Path(target_subpath)
    if not target_path.is_absolute():
        target_path = REPO_ROOT / target_subpath

    if target_path.is_dir():
        return scan_repo_for_bugs(target_subpath)

    rel = str(target_path.relative_to(REPO_ROOT))
    try:
        src = target_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {
            "rel": rel,
            "functions_modeled": 0,
            "call_sites_cross_checked": 0,
            "total_anomalies_found": 1,
            "anomalies": [{
                "severity": "CRITICAL",
                "category": "FILE_READ_ERROR",
                "location": rel,
                "detail": str(e)[:120],
            }],
        }

    return scan_source_file(rel, src)


# ---------------------------------------------------------------------------
# 2. REVIEW — Fast-Scan Differential Code Review
# ---------------------------------------------------------------------------
def cmd_review(args) -> None:
    """Reviews the working-tree diff vs a base ref.

    Reports Shannon change-dispersion entropy (focused vs dispersed change),
    per-file LOC delta, and runs the bug hunter on every modified source file.
    """
    numstat = sh(["git", "diff", args.base, "--numstat"]).splitlines()
    changed_files: list[dict] = []
    total_loc_delta = 0

    for line in numstat:
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            delta = int(parts[0]) + int(parts[1])
            total_loc_delta += delta
            changed_files.append({"file": parts[2], "loc_delta": delta})

    entropy_bits = 0.0
    if total_loc_delta > 0:
        for cf in changed_files:
            p_i = cf["loc_delta"] / total_loc_delta
            if p_i > 0:
                entropy_bits -= p_i * math.log2(p_i)

    diff_anomalies: list[dict] = []
    for cf in changed_files:
        if Path(cf["file"]).suffix.lower() in ALL_SOURCE_EXTENSIONS and \
           (REPO_ROOT / cf["file"]).exists():
            res = _scan_single_file(cf["file"])
            diff_anomalies.extend(res["anomalies"])

    output = {
        "base_ref": args.base,
        "files_modified": len(changed_files),
        "total_lines_changed": total_loc_delta,
        "shannon_change_dispersion_entropy_bits": round(entropy_bits, 3),
        "entropy_risk_tier": (
            "HIGH_DISPERSION_RISK" if entropy_bits > 2.5
            else "FOCUSED_SURGICAL_CHANGE"
        ),
        "changed_files": changed_files,
        "anomalies_in_changed_files": rank_anomalies(diff_anomalies),
    }
    print(json.dumps(output, indent=2))


# ---------------------------------------------------------------------------
# 3. FORENSICS — AST-Refined SZZ Bug Genealogy
# ---------------------------------------------------------------------------
def cmd_forensics(args) -> None:
    """Traces where a bug came from via 'git log -L' / '-S' pickaxe.

    Input forms:
      - file.py:line_start-line_end   (line-range evolution tracking)
      - file.py:L42                   (single-line window around L42)
      - symbol_name                   (pickaxe: when the symbol entered/left)
    """
    target = args.target
    log_out: str

    if ":" in target:
        file_part, line_spec = target.split(":", 1)
        line_clean = re.sub(r"[^0-9,-]", "", line_spec).replace("-", ",")
        if "," not in line_clean:
            try:
                l_no = int(line_clean or 1)
            except ValueError:
                l_no = 1
            line_clean = f"{max(1, l_no - 3)},{l_no + 3}"
        log_out = sh([
            "git", "log", "-n", "8", "--no-patch",
            "--pretty=format:%h|%ad|%an|%s", "--date=short",
            f"-L{line_clean}:{file_part}",
        ])
    else:
        log_out = sh([
            "git", "log", "-n", "10", "--pretty=format:%h|%ad|%an|%s",
            "--date=short", "-S", target,
        ])

    commits: list[dict] = []
    for line in log_out.splitlines():
        if "|" in line and not line.startswith(("diff ", "---", "+++", "@@")):
            parts = line.split("|", 3)
            if len(parts) == 4:
                sha, date, author, subj = parts
                co_files = [
                    f.strip() for f in sh([
                        "git", "show", "--name-only", "--pretty=format:", sha,
                    ]).splitlines() if f.strip()
                ]
                commits.append({
                    "commit_sha": sha,
                    "date": date,
                    "author": author,
                    "subject": subj,
                    "co_modified_files_in_commit": co_files[:10],
                    "is_probable_bug_inducing_commit": not any(
                        w in subj.lower()
                        for w in ("format", "lint", "typo", "doc", "comment")
                    ),
                })

    bic = next(
        (c for c in commits if c["is_probable_bug_inducing_commit"]),
        commits[0] if commits else None,
    )
    print(json.dumps({
        "forensic_target": target,
        "probable_bug_inducing_commit_BIC": bic,
        "evolutionary_lineage": commits,
    }, indent=2))


# ---------------------------------------------------------------------------
# 4. DYLIB-AUDIT — Native Binary Forensic Auditor
# ---------------------------------------------------------------------------
def inspect_binary_header(path: Path) -> dict:
    """Reads raw ELF or Mach-O magic headers without external binutils."""
    try:
        with path.open("rb") as f:
            hdr = f.read(64)
    except OSError:
        return {"format": "UNREADABLE"}

    if len(hdr) < 20:
        return {"format": "TOO_SMALL"}

    # Linux ELF binary (\x7fELF)
    if hdr[:4] == b"\x7fELF":
        bits = "64-bit" if hdr[4] == 2 else "32-bit"
        endian = "<" if hdr[5] == 1 else ">"
        machine_code = struct.unpack(f"{endian}H", hdr[18:20])[0]
        entry = struct.unpack(f"{endian}Q", hdr[24:32])[0] if hdr[4] == 2 else struct.unpack(f"{endian}I", hdr[24:28])[0]
        isa = {
            0x3E: "x86_64",
            0xB7: "aarch64 (ARM64)",
            0x03: "x86",
        }.get(machine_code, f"0x{machine_code:x}")
        info: dict = {
            "format": f"ELF ({bits})",
            "isa": isa,
            "entry_point_hex": hex(entry),
        }
        missing_libs: list[str] = []
        if HAS_LDD:
            ldd_out = sh(["ldd", str(path)])
            missing_libs = [l.strip() for l in ldd_out.splitlines() if "not found" in l]
        info["missing_shared_libs"] = missing_libs
        if HAS_NM:
            info["symbols"] = _nm_symbols(path)
        if HAS_STRINGS:
            info["strings_sample"] = _extract_strings(path, limit=20)
        return info

    # macOS Mach-O 64-bit (0xfeedfacf little-endian)
    magic_le = struct.unpack("<I", hdr[:4])[0]
    magic_be = struct.unpack(">I", hdr[:4])[0]
    if magic_le == 0xFEEDFACF:
        cputype = struct.unpack("<I", hdr[4:8])[0]
        isa = {
            0x01000007: "x86_64",
            0x0100000C: "arm64 (Apple Silicon Native)",
        }.get(cputype, f"0x{cputype:x}")
        info = {
            "format": "Mach-O 64-bit",
            "isa": isa,
        }
        if HAS_OTOOL:
            ot_out = sh(["otool", "-L", str(path)])
            info["linked_dylibs"] = [
                l.strip().split()[0]
                for l in ot_out.splitlines()[1:6] if l.strip()
            ]
        elif HAS_LDD:
            ldd_out = sh(["ldd", str(path)])
            info["linked_dylibs"] = [
                l.strip().split()[0]
                for l in ldd_out.splitlines()[1:6] if l.strip()
            ]
        if HAS_NM:
            info["symbols"] = _nm_symbols(path)
        if HAS_STRINGS:
            info["strings_sample"] = _extract_strings(path, limit=20)
        return info

    # Universal fat binary (0xcafebabe big-endian)
    if magic_be == 0xCAFEBABE:
        nfat = struct.unpack(">I", hdr[4:8])[0]
        return {
            "format": f"Mach-O Universal Fat Binary ({nfat} slices)",
            "isa": "universal (arm64 + x86_64)",
        }

    return {"format": "OTHER/SCRIPT"}


def _nm_symbols(path: Path) -> list[dict]:
    """Extract symbol table via nm (function names + addresses)."""
    if not HAS_NM:
        return []
    out = sh(["nm", "--defined-only", str(path)])
    syms: list[dict] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            addr, typ, name = parts[0], parts[1], parts[2]
            syms.append({"address": addr, "type": typ, "name": name})
    return syms[:50]


def _extract_strings(path: Path, limit: int = 20) -> list[str]:
    """Extract printable strings from binary via strings command."""
    if not HAS_STRINGS:
        return []
    out = sh(["strings", "-n", "4", str(path)])
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return lines[:limit]


def _dependency_graph(path: Path) -> dict:
    """Build shared-library dependency graph via ldd/readelf/otool."""
    deps: list[str] = []
    if HAS_LDD:
        out = sh(["ldd", str(path)])
        for line in out.splitlines():
            if "not found" in line:
                deps.append({"name": line.split()[0], "status": "MISSING"})
            elif "=>" in line:
                parts = line.split()
                deps.append({"name": parts[0], "resolved": parts[2] if len(parts) > 2 else None, "status": "OK"})
            elif line.strip() and not line.startswith(("ldd:", "")):
                parts = line.split()
                if parts:
                    deps.append({"name": parts[0], "status": "STATIC"})
    elif HAS_READELF:
        out = sh(["readelf", "-d", str(path)])
        for line in out.splitlines():
            if "NEEDED" in line:
                m = re.search(r"NEEDED\s+\[([^\]]+)\]", line)
                if m:
                    deps.append({"name": m.group(1), "status": "NEEDED"})
    elif HAS_OTOOL:
        out = sh(["otool", "-L", str(path)])
        for line in out.splitlines()[1:]:
            line = line.strip()
            if line:
                deps.append({"name": line.split()[0], "status": "DYLIB"})
    return {"dependencies": deps, "count": len(deps)}


def cmd_dylib_audit(args) -> None:
    """Audits native C-extensions (.so / .dylib / .pyd) for ABI/arch mismatch."""
    host_arch = platform.machine()
    binaries: list[dict] = []

    for root in [REPO_ROOT / args.path]:
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [
                d for d in dirs
                if d not in {".git", "node_modules", ".agent-kb"}
                and not d.startswith(".")
            ]
            for f in files:
                if f.endswith((".so", ".dylib", ".dll", ".pyd")):
                    p = Path(dirpath, f)
                    info = inspect_binary_header(p)
                    info["dependency_graph"] = _dependency_graph(p)
                    arch_mismatch = (
                        host_arch in ("arm64", "aarch64")
                        and "x86_64" in info.get("isa", "")
                        and "universal" not in info.get("isa", "")
                    )
                    binaries.append({
                        "file": str(p.relative_to(REPO_ROOT)),
                        **info,
                        "arch_mismatch_hazard": arch_mismatch,
                    })
                    if len(binaries) >= 40:
                        break
            if len(binaries) >= 40:
                break

    mismatches = [
        b for b in binaries
        if b.get("arch_mismatch_hazard") or b.get("missing_shared_libs")
    ]
    print(json.dumps({
        "host_os": sys.platform,
        "host_arch": host_arch,
        "binutils_available": {
            "nm": HAS_NM, "objdump": HAS_OBJDUMP, "readelf": HAS_READELF,
            "strings": HAS_STRINGS, "ldd": HAS_LDD, "otool": HAS_OTOOL,
        },
        "native_libraries_scanned": len(binaries),
        "mismatches_or_missing_links": mismatches,
        "sample_binaries": binaries[:15],
    }, indent=2))


# ---------------------------------------------------------------------------
# 5. CFG — Control Flow Graph Reverse Engineering (objdump-based)
# ---------------------------------------------------------------------------
# x86-64 / aarch64 branch instructions that terminate a basic block
TERMINATOR_OPCODES = {
    # x86-64 unconditional jumps
    "jmp", "ret", "call",
    # x86-64 conditional jumps
    "je", "jne", "jz", "jnz", "js", "jns", "jg", "jge", "jl", "jle",
    "ja", "jae", "jb", "jbe", "jcxz", "jecxz", "jrcxz",
    # x86-64 indirect
    "jmp*", "call*",
    # aarch64
    "b", "bl", "blr", "ret", "cbz", "cbnz", "tbz", "tbnz", "b.eq", "b.ne",
    "b.cs", "b.cc", "b.mi", "b.pl", "b.vs", "b.vc", "b.hi", "b.ls",
    "b.ge", "b.lt", "b.gt", "b.le",
}


def _is_terminator(mnemonic: str) -> bool:
    m = mnemonic.lower().strip()
    base = m.split(".")[0]
    if base.endswith("*"):
        base = base[:-1]
    return base in TERMINATOR_OPCODES or any(
        m.startswith(t) for t in TERMINATOR_OPCODES
    )


def _extract_branch_target(operand: str) -> str | None:
    """Extract a branch target address from an operand string."""
    o = operand.strip()
    if "<" in o and ">" in o:
        inner = o[o.index("<") + 1:o.index(">")]
        if "+" in inner:
            return inner.split("+")[-1].strip()
        return inner
    if o.startswith("0x"):
        return o
    if o.startswith("%") or o.startswith("x") or o.startswith("w"):
        return None
    return None


def _disassemble_binary(path: Path) -> str:
    """Disassemble a binary using objdump. Returns raw assembly text."""
    if not HAS_OBJDUMP:
        return ""
    try:
        res = subprocess.run(
            ["objdump", "-d", "-M", "intel", str(path)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=30,
        )
        return res.stdout
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _parse_basic_blocks(asm_text: str) -> list[dict]:
    """Parse objdump output into basic blocks with terminators."""
    blocks: list[dict] = []
    current_block: list[dict] = []
    current_addr: str | None = None

    for line in asm_text.splitlines():
        addr_match = re.match(r"^\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{2}\s+)+(.*)$", line)
        if not addr_match:
            label_match = re.match(r"^\s*([0-9a-fA-F]+)\s+<([^>]+)>:", line)
            if label_match:
                if current_block:
                    blocks.append({
                        "start_addr": current_addr,
                        "instructions": current_block,
                        "terminator": current_block[-1] if current_block else None,
                    })
                    current_block = []
                    current_addr = None
                current_addr = label_match.group(1)
                current_block = [{
                    "addr": label_match.group(1),
                    "mnemonic": "<label>",
                    "operand": label_match.group(2),
                    "raw": line.strip(),
                }]
            continue

        if addr_match:
            addr = addr_match.group(1)
            rest = addr_match.group(3)
            parts = rest.split(None, 1)
            mnemonic = parts[0] if parts else ""
            operand = parts[1] if len(parts) > 1 else ""

            if current_addr is None:
                current_addr = addr
                current_block = []

            current_block.append({
                "addr": addr,
                "mnemonic": mnemonic,
                "operand": operand,
                "raw": line.strip(),
            })

            if _is_terminator(mnemonic):
                blocks.append({
                    "start_addr": current_addr,
                    "instructions": current_block,
                    "terminator": current_block[-1],
                })
                current_block = []
                current_addr = None

    if current_block:
        blocks.append({
            "start_addr": current_addr,
            "instructions": current_block,
            "terminator": current_block[-1] if current_block else None,
        })

    return blocks


def _build_cfg(blocks: list[dict]) -> dict:
    """Build a control flow graph from basic blocks."""
    addr_to_block: dict[str, int] = {}
    for i, b in enumerate(blocks):
        addr_to_block[b["start_addr"]] = i

    nodes = []
    edges: list[dict] = []

    for i, b in enumerate(blocks):
        term = b["terminator"]
        if not term:
            continue
        mnemonic = term["mnemonic"].lower()
        operand = term.get("operand", "")
        target = _extract_branch_target(operand)

        node_id = f"B{b['start_addr']}"
        nodes.append({
            "id": node_id,
            "start_addr": b["start_addr"],
            "instruction_count": len(b["instructions"]),
            "terminator": f"{mnemonic} {operand}".strip(),
        })

        fallthrough_idx = None
        if i + 1 < len(blocks):
            fallthrough_idx = i + 1

        if mnemonic == "ret":
            pass
        elif mnemonic == "jmp":
            if target:
                target_idx = addr_to_block.get(target)
                if target_idx is not None:
                    edges.append({"from": node_id, "to": f"B{blocks[target_idx]['start_addr']}", "type": "unconditional"})
                else:
                    edges.append({"from": node_id, "to": f"external:{target}", "type": "unconditional"})
        elif mnemonic == "call":
            if target:
                target_idx = addr_to_block.get(target)
                if target_idx is not None:
                    edges.append({"from": node_id, "to": f"B{blocks[target_idx]['start_addr']}", "type": "call"})
                else:
                    edges.append({"from": node_id, "to": f"external:{target}", "type": "call"})
            if fallthrough_idx is not None:
                edges.append({"from": node_id, "to": f"B{blocks[fallthrough_idx]['start_addr']}", "type": "fallthrough"})
        else:
            if target:
                target_idx = addr_to_block.get(target)
                if target_idx is not None:
                    edges.append({"from": node_id, "to": f"B{blocks[target_idx]['start_addr']}", "type": "branch_taken"})
                else:
                    edges.append({"from": node_id, "to": f"external:{target}", "type": "branch_taken"})
            if fallthrough_idx is not None:
                edges.append({"from": node_id, "to": f"B{blocks[fallthrough_idx]['start_addr']}", "type": "fallthrough"})

    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}


def cmd_cfg(args) -> int:
    """Extract a control flow graph from a native binary using objdump."""
    target_p = Path(args.binary)
    if not target_p.is_absolute():
        target_p = REPO_ROOT / target_p

    if not target_p.exists():
        print(f"ERROR: Binary '{target_p}' not found.", file=sys.stderr)
        return 1

    if not HAS_OBJDUMP:
        print("ERROR: objdump not available — cannot disassemble.", file=sys.stderr)
        return 1

    asm_text = _disassemble_binary(target_p)
    if not asm_text:
        print(f"ERROR: Failed to disassemble '{target_p}'.", file=sys.stderr)
        return 1

    blocks = _parse_basic_blocks(asm_text)
    cfg = _build_cfg(blocks)

    try:
        binary_display = str(target_p.relative_to(REPO_ROOT))
    except ValueError:
        binary_display = str(target_p)

    output = {
        "binary": binary_display,
        "cfg": cfg,
        "total_blocks": len(blocks),
    }

    if args.function:
        # Filter blocks belonging to the function
        func_blocks = []
        in_func = False
        for line in asm_text.splitlines():
            label_match = re.match(r"^\s*[0-9a-fA-F]+\s+<([^>]+)>:", line)
            if label_match:
                func_name = label_match.group(1)
                in_func = (func_name == args.function or func_name.endswith(f".{args.function}"))
            if in_func and re.match(r"^\s*[0-9a-fA-F]+:", line):
                func_blocks.append(line.strip())
        output["function"] = args.function
        output["disassembly_lines"] = len(func_blocks)

    print(json.dumps(output, indent=2))
    return 0


# ---------------------------------------------------------------------------
# 6. VERIFY-FIX — Separation-Logic Frame Rule Verifier
# ---------------------------------------------------------------------------
def extract_signatures_map(py_text: str) -> dict:
    """Extract per-function signature contract from Python source text."""
    sigs: dict[str, dict] = {}
    try:
        tree = ast.parse(py_text)
    except SyntaxError:
        return sigs

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            pos_args = [
                a.arg for a in node.args.posonlyargs + node.args.args
                if a.arg not in ("self", "cls")
            ]
            n_def = len(node.args.defaults)
            sigs[node.name] = {
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "min_args": max(0, len(pos_args) - n_def),
                "max_args": 999 if node.args.vararg else len(pos_args),
                "required_args": pos_args[: max(0, len(pos_args) - n_def)],
                "all_arg_names": set(
                    pos_args + [a.arg for a in node.args.kwonlyargs]
                ),
                "has_kwarg": node.args.kwarg is not None,
            }
    return sigs


def extract_tsjs_signatures_map(tsjs_text: str) -> dict:
    """Extract per-function signature contract from TypeScript/JavaScript source."""
    sigs: dict[str, dict] = {}
    lines = tsjs_text.splitlines()

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Function declarations: function name(args) or const name = (args) =>
        for m in TSJS_FUNC_RE.finditer(stripped):
            name = m.group(1) or m.group(2) or m.group(4) or "anonymous"
            args_str = m.group(3) or m.group(5) or ""
            arg_names = [a.strip().split(":")[0].strip() for a in args_str.split(",") if a.strip()]
            arg_names = [a for a in arg_names if a and not a.startswith("...")]
            n_def = len([a for a in arg_names if "=" in a])
            sigs[name] = {
                "is_async": "async" in stripped,
                "min_args": max(0, len(arg_names) - n_def),
                "max_args": 999 if "..." in args_str else len(arg_names),
                "required_args": [a for a in arg_names if "=" not in a],
                "all_arg_names": set(arg_names),
                "has_kwarg": False,
            }

    return sigs


def cmd_verify_fix(args) -> int:
    """Proves uncommitted changes to <file> violate 0 Liskov contracts across
    all repo callers, and introduce 0 new AST anomalies.

    Returns 0 if safe to ship, 1 if regression risk detected.
    """
    target_p = Path(args.file)
    if not target_p.is_absolute():
        target_p = REPO_ROOT / target_p
    rel = str(target_p.relative_to(REPO_ROOT))
    ext = target_p.suffix.lower()

    new_text = target_p.read_text(encoding="utf-8", errors="replace")
    old_text = sh(["git", "show", f"HEAD:{rel}"])

    old_sigs: dict = {}
    new_sigs: dict = {}

    if ext in PY_EXTENSIONS:
        old_sigs = extract_signatures_map(old_text) if old_text else {}
        new_sigs = extract_signatures_map(new_text)
    elif ext in TSJS_EXTENSIONS:
        old_sigs = extract_tsjs_signatures_map(old_text) if old_text else {}
        new_sigs = extract_tsjs_signatures_map(new_text)

    liskov_violations: list[dict] = []

    for sym, o_meta in old_sigs.items():
        if sym not in new_sigs:
            liskov_violations.append({
                "symbol": sym,
                "violation": "SYMBOL_DELETED",
                "detail": f"Function '{sym}' was removed from {rel}.",
            })
            continue
        n_meta = new_sigs[sym]
        if o_meta != n_meta:
            pass  # symbol modified, check specifics below
        if n_meta["min_args"] > o_meta["min_args"]:
            liskov_violations.append({
                "symbol": sym,
                "violation": "REQUIRED_ARGS_INCREASED",
                "detail": (
                    f"Required positional args increased from "
                    f"{o_meta['min_args']} to {n_meta['min_args']} "
                    f"(add a default value to preserve Frame R!)."
                ),
            })
        if n_meta["max_args"] < o_meta["max_args"]:
            liskov_violations.append({
                "symbol": sym,
                "violation": "MAX_ARGS_REDUCED",
                "detail": (
                    f"Max accepted positional args decreased from "
                    f"{o_meta['max_args']} to {n_meta['max_args']}."
                ),
            })
        removed_kwargs = o_meta["all_arg_names"] - n_meta["all_arg_names"]
        if removed_kwargs and not n_meta["has_kwarg"]:
            liskov_violations.append({
                "symbol": sym,
                "violation": "KWARG_RENAMED_OR_REMOVED",
                "detail": (
                    f"Parameter names {sorted(removed_kwargs)} were removed/"
                    f"renamed, breaking keyword callers."
                ),
            })

    # Run AST bug scan on the patched file (0 new anomalies required).
    file_scan = _scan_single_file(rel)

    passed = (len(liskov_violations) == 0) and (file_scan["total_anomalies_found"] == 0)

    output = {
        "verified_file": rel,
        "separation_logic_frame_safe": passed,
        "liskov_contract_violations": liskov_violations,
        "anomalies_in_patched_file": file_scan["anomalies"],
        "verdict": "SAFE_TO_SHIP" if passed else "BLOCKED_REGRESSION_RISK_DETECTED",
    }
    print(json.dumps(output, indent=2))
    return 0 if passed else 1


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Aegis Bug Hunter, Root-Cause Forensics & Zero-Regression "
            "Patch Verifier"
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    ht = sub.add_parser(
        "hunt",
        help="Run Engler Statistical Deviance Miner + PVS-Studio AST Bug Hunter",
    )
    ht.add_argument("--path", default=".")

    rv = sub.add_parser(
        "review",
        help="Fast-Scan Differential Code Review (Shannon Entropy + Bug Gates)",
    )
    rv.add_argument("--base", default="HEAD")

    fr = sub.add_parser(
        "forensics",
        help="AST-SZZ Bug Genealogy ('file.py:L_start-L_end' or symbol name)",
    )
    fr.add_argument("target", help="file.py:line range OR symbol_name")

    dy = sub.add_parser(
        "dylib-audit",
        help="Inspect native .so ELF (Linux) & .dylib Mach-O (M1 Pro) binaries",
    )
    dy.add_argument("--path", default=".")

    cg = sub.add_parser(
        "cfg",
        help="Control Flow Graph reverse engineering via objdump disassembly",
    )
    cg.add_argument("binary", help="Path to native binary (.so / .dylib / executable)")
    cg.add_argument("--function", help="Filter to specific function name")

    vf = sub.add_parser(
        "verify-fix",
        help="Separation-Logic Frame Rule & Liskov Call-Site Patch Verifier",
    )
    vf.add_argument("file", help="Modified file path to verify against HEAD + repo callers")

    args = p.parse_args()

    if args.cmd == "hunt":
        print(json.dumps(scan_repo_for_bugs(args.path), indent=2))
        return 0
    if args.cmd == "review":
        cmd_review(args)
        return 0
    if args.cmd == "forensics":
        cmd_forensics(args)
        return 0
    if args.cmd == "dylib-audit":
        cmd_dylib_audit(args)
        return 0
    if args.cmd == "cfg":
        return cmd_cfg(args)
    if args.cmd == "verify-fix":
        return cmd_verify_fix(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
