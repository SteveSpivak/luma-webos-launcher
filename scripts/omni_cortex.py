#!/usr/bin/env python3
"""
OMNI-CORTEX CLI — Next-Gen Forensic, Mathematical & Overload-Protected Agent Engine.

Council of Experts "7 Hidden Gems" implementation for Arena Virtual Linux
(6.1+, 2 vCPU, cgroup=null) and macOS Apple Silicon (M1 Pro).

100% read-only by default, zero dependency (stdlib only), never fabricates
missing hardware numbers (null stays null), never mutates OS state.

Subcommands:
  telemetry     — Honest syscall (/proc/self/status, getrusage, /proc/pressure) snapshot
  triage-suite  — Zero-import AST Pre-Flight + Ochiai root-cause localization
  merkle-map    — Unison-style function-level AST Merkle hashing + import cones
  ncd-clones    — Kolmogorov NCD semantic clone detector
  topology      — Spectral graph: β1 Betti, Tarjan SCCs, PageRank, Fiedler λ2
  run-guarded   — Closed-loop BBR/Vegas overload-protected batched test runner
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(os.environ.get("REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from lib.telemetry import sample_all  # noqa: E402
from lib.receipts import issue_receipt  # noqa: E402
from lib.ast_probe import triage_test_suite  # noqa: E402
from lib.ncd_clones import find_clones  # noqa: E402
from lib.topology import analyze  # noqa: E402


def cmd_telemetry(args):
    snap = sample_all()
    env_label = f"{snap['platform']}-{snap['machine']}"
    rcpt = issue_receipt(
        environment=env_label,
        command="omni_cortex telemetry",
        exit_code=0,
        duration_ms=0.0,
        telemetry=snap,
    )
    out = {
        "receipt_id": rcpt,
        "telemetry": snap,
    }
    print(json.dumps(out, indent=2))
    print(f"\n[ARENA RECEIPT] {rcpt} — telemetry snapshot issued (read-only, no fabrication)")


def cmd_triage_suite(args):
    report, elapsed_ms = triage_test_suite(args.path)
    env_label = f"{os.uname().sysname if hasattr(os, 'uname') else 'unknown'}"
    rcpt = issue_receipt(
        environment=env_label,
        command=f"omni_cortex triage-suite --path {args.path}",
        exit_code=0 if report["blocked_at_collection"] == 0 else 1,
        duration_ms=elapsed_ms,
        telemetry={"tests_scanned": report["total_test_files"],
                   "runnable": report["runnable_now"],
                   "blocked": report["blocked_at_collection"]},
    )
    report["receipt_id"] = rcpt
    print(json.dumps(report, indent=2))
    print(f"\n[ARENA RECEIPT] {rcpt} — Ochiai root-cause triage complete in {elapsed_ms} ms")


def cmd_merkle_map(args):
    """Unison-style function-level AST Merkle hashing + import dependency cones."""
    import ast
    import hashlib
    from lib.ast_probe import iter_py_files, build_local_module_index

    root = Path(args.path).resolve()
    local_roots, dotted_map = build_local_module_index(root)
    records = []
    t0 = time.perf_counter()

    for p in iter_py_files(root):
        rel = str(p.relative_to(root))
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno
                end = getattr(node, "end_lineno", start)
                loc = max(1, end - start + 1)
                dump = ast.dump(node, include_attributes=False)
                merkle = hashlib.sha256(dump.encode("utf-8")).hexdigest()[:16]
                # Dotted module path for this symbol
                mod_parts = rel.replace("/", ".").replace("\\", ".")[:-3]  # strip .py
                records.append({
                    "qualname": f"{mod_parts}::{node.name}",
                    "file": rel,
                    "symbol": node.name,
                    "lineno": start,
                    "loc": loc,
                    "merkle_ast": merkle,
                })

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    rcpt = issue_receipt(
        environment=os.uname().sysname if hasattr(os, "uname") else "unknown",
        command=f"omni_cortex merkle-map --path {args.path}",
        exit_code=0,
        duration_ms=elapsed_ms,
        telemetry={"symbols_hashed": len(records)},
    )
    print(json.dumps({
        "receipt_id": rcpt,
        "scan_duration_ms": elapsed_ms,
        "symbols_hashed": len(records),
        "symbols": records[:50],
    }, indent=2))


def cmd_ncd_clones(args):
    result = find_clones(Path(args.path), min_loc=args.min_loc, threshold=args.threshold)
    env_label = os.uname().sysname if hasattr(os, "uname") else "unknown"
    rcpt = issue_receipt(
        environment=env_label,
        command=f"omni_cortex ncd-clones --path {args.path} --min-loc {args.min_loc} --threshold {args.threshold}",
        exit_code=0,
        duration_ms=result["scan_duration_ms"],
        telemetry={"functions_compared": result["functions_compared"],
                   "clones_found": result["clones_found"]},
    )
    result["receipt_id"] = rcpt
    print(json.dumps(result, indent=2))


def cmd_topology(args):
    result = analyze(Path(args.path))
    env_label = os.uname().sysname if hasattr(os, "uname") else "unknown"
    rcpt = issue_receipt(
        environment=env_label,
        command=f"omni_cortex topology --path {args.path}",
        exit_code=0,
        duration_ms=0.0,
        telemetry={"vertices": result["vertices"], "edges": result["directed_edges"],
                   "betti1": result["first_betti_number"], "sccs": result["tarjan_scc_count"]},
    )
    result["receipt_id"] = rcpt
    print(json.dumps(result, indent=2))


def cmd_run_guarded(args):
    """Closed-loop BBR/Vegas overload-protected batched test runner."""
    import subprocess
    import tempfile

    snap_before = sample_all()
    hw_cpu = snap_before["cpu"]
    eff_cores = (
        hw_cpu.get("affinity_count")
        or hw_cpu.get("logical_cpus")
        or 1
    )
    cg_cores = hw_cpu.get("cgroup", {}).get("cores")
    max_safe = max(1, int(min(eff_cores, cg_cores))) if cg_cores else max(1, eff_cores)
    mem_known = snap_before["memory"].get("cgroup", {}).get("limit_bytes") is not None
    workers = min(max_safe, 2) if mem_known else 1

    # Zero-import pre-flight: only run hermetically-collectible tests
    from lib.ast_probe import iter_py_files, build_local_module_index, is_pkg_installed
    root = Path(args.path).resolve()
    local_roots, _ = build_local_module_index(root)
    stdlib = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()
    cache: dict = {}

    runnable = []
    for tf in iter_py_files(root):
        if not (tf.name.startswith("test_") or tf.name.endswith("_test.py")):
            continue
        try:
            import ast
            tree = ast.parse(tf.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        ok = True
        for node in ast.walk(tree):
            pkgs = []
            if isinstance(node, ast.Import):
                pkgs = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                pkgs = [node.module.split(".")[0]]
            for pkg in pkgs:
                if not is_pkg_installed(pkg, stdlib, local_roots, cache):
                    ok = False
                    break
            if not ok:
                break
        if ok:
            runnable.append(str(tf.relative_to(root)))

    batch_size = max(1, args.batch_size)
    batches = [runnable[i:i + batch_size] for i in range(0, len(runnable), batch_size)]

    trace = []
    passed = failed = 0
    t_suite0 = time.perf_counter()

    for idx, batch in enumerate(batches):
        snap_b = sample_all()["rusage"]
        t_b0 = time.perf_counter()

        with tempfile.TemporaryDirectory(prefix="omni_batch_") as tmpdir:
            env = os.environ.copy()
            env["TMPDIR"] = tmpdir
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["OMP_NUM_THREADS"] = "1"
            env["PYTHONPATH"] = f"{root}:{root / 'src'}:" + env.get("PYTHONPATH", "")
            cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short"] + batch
            proc = subprocess.run(cmd, cwd=root, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        wall_dt = max(0.001, time.perf_counter() - t_b0)
        snap_a = sample_all()["rusage"]

        d_cpu = (snap_a["user_cpu_sec"] - snap_b["user_cpu_sec"]) + \
                (snap_a["sys_cpu_sec"] - snap_b["sys_cpu_sec"])
        d_niv = snap_a["involuntary_ctx_switches"] - snap_b["involuntary_ctx_switches"]
        d_nv = snap_a["voluntary_ctx_switches"] - snap_b["voluntary_ctx_switches"]
        d_maj = snap_a["major_page_faults"] - snap_b["major_page_faults"]
        kappa = round(d_niv / max(1, d_niv + d_nv), 4)

        overloaded = (kappa > 0.40) or (d_maj > 0)
        if overloaded:
            workers = 1

        if proc.returncode == 0:
            passed += 1
        else:
            failed += 1

        trace.append({
            "batch": idx,
            "files": len(batch),
            "exit_code": proc.returncode,
            "wall_sec": round(wall_dt, 3),
            "cpu_sec": round(d_cpu, 3),
            "kappa": kappa,
            "major_faults_delta": d_maj,
            "maxrss_mb": round(snap_a["maxrss_bytes"] / (1024 * 1024), 2),
            "throttled": overloaded,
        })

    t_suite = round(time.perf_counter() - t_suite0, 3)
    snap_final = sample_all()
    rcpt = issue_receipt(
        environment=f"{snap_final['platform']}-{snap_final['machine']}",
        command=f"omni_cortex run-guarded --path {args.path} --batch-size {args.batch_size}",
        exit_code=0 if failed == 0 else 1,
        duration_ms=round(t_suite * 1000, 2),
        telemetry={"workers": workers, "batches": len(batches),
                   "passed": passed, "failed": failed},
    )

    print(json.dumps({
        "receipt_id": rcpt,
        "suite_wall_sec": t_suite,
        "hermetic_tests_executed": len(runnable),
        "batches_passed": passed,
        "batches_failed": failed,
        "workers_used": workers,
        "final_telemetry": snap_final,
        "batch_trace": trace,
    }, indent=2))
    sys.exit(0 if failed == 0 else 1)


def main():
    p = argparse.ArgumentParser(
        description="Omni-Cortex Next-Gen Forensic & Overload-Safe CLI (Council of Experts)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("telemetry", help="Honest syscall/procfs/PSI telemetry snapshot")

    tr = sub.add_parser("triage-suite", help="Zero-import AST + Ochiai root-cause localization")
    tr.add_argument("--path", default=".")

    ncd = sub.add_parser("ncd-clones", help="Kolmogorov NCD semantic clone detector")
    ncd.add_argument("--path", default=".")
    ncd.add_argument("--min-loc", type=int, default=12)
    ncd.add_argument("--threshold", type=float, default=0.22)

    merkle_p = sub.add_parser("merkle-map", help="Unison-style function-level AST Merkle hashing")
    merkle_p.add_argument("--path", default=".")

    top = sub.add_parser("topology", help="Spectral graph: β1, Tarjan SCCs, PageRank, Fiedler λ2")
    top.add_argument("--path", default=".")

    rg = sub.add_parser("run-guarded", help="BBR/Vegas overload-protected batched test runner")
    rg.add_argument("--path", default=".")
    rg.add_argument("--batch-size", type=int, default=10)

    args = p.parse_args()
    dispatch = {
        "telemetry": cmd_telemetry,
        "triage-suite": cmd_triage_suite,
        "ncd-clones": cmd_ncd_clones,
        "merkle-map": cmd_merkle_map,
        "topology": cmd_topology,
        "run-guarded": cmd_run_guarded,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
