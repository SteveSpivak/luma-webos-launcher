#!/usr/bin/env python3
"""
COUNCIL ENTRY — Single unified entry point to all Council CLI capabilities.

Drop this file (plus the sibling scripts) into any repo and run:

    python3 council_entry.py <subcommand> [options]

Subcommands are grouped by capability:

  INDEX / FORENSICS
    sync            O(Δ) wait-free polyglot indexer (symbols, edges, channels)
    read            Focal + skeleton AST reader (85% token cut)
    diagnose-setup  Import-time trap & monorepo root diagnostician
    state-lineage   Bipartite state-channel graph (writers vs readers)
    checkpoint      3ms git ODB shadow tree (instant undo)
    bench           MAD + Hodges-Lehmann A/B benchmark

  BUG HUNTING / PATCH VERIFICATION
    hunt            Engler deviance mining + PVS-Studio AST anomalies
    review          Fast-scan differential review (Shannon entropy)
    forensics       AST-Refined SZZ bug genealogy (BIC detection)
    dylib-audit     Native binary audit (.so ELF / .dylib Mach-O)
    cfg             Control-flow graph extraction via objdump
    verify-fix      Separation-Logic Frame Rule + Liskov call-site check

  TOOL COMPRESSION
    run             Compress any command output into @H-XXXX handle
    deref           Losslessly dereference lines/regex from a handle
    bench-compression Rate-distortion benchmark (5,255-error stress test)
    batch-compress  Parallel compress of multiple files

  ORCHESTRATION
    full            Run the complete council pipeline end-to-end
    receipt-chain   Display chained RCPT receipts
    drift           Cross-repo drift detection (7 categories)
    record-fix      Record fix provenance (what/where/why/how)

  UTILITY
    help            Show this help

Every subcommand is zero-external-dependency (pure Python 3.11 stdlib) and
optionally uses system binutils (nm, objdump, readelf, strings, ldd) when
present. All emit tamper-evident RCPT receipts via arena_guard.py exec.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("REPO_ROOT", ".")).resolve()
KIT_DIR = Path(__file__).resolve().parent

SCRIPT_MAP = {
    # Index / forensics
    "sync": "nexus_agent_os.py",
    "read": "nexus_agent_os.py",
    "diagnose-setup": "nexus_agent_os.py",
    "state-lineage": "nexus_agent_os.py",
    "checkpoint": "nexus_agent_os.py",
    "bench": "nexus_agent_os.py",
    # Bug hunting / patch verification
    "hunt": "aegis_bug_hunter.py",
    "review": "aegis_bug_hunter.py",
    "forensics": "aegis_bug_hunter.py",
    "dylib-audit": "aegis_bug_hunter.py",
    "cfg": "aegis_bug_hunter.py",
    "verify-fix": "aegis_bug_hunter.py",
    # Tool compression
    "run": "tool_latent_codec.py",
    "deref": "tool_latent_codec.py",
    "bench-compression": "tool_latent_codec.py",
    "batch-compress": "tool_latent_codec.py",
    # Orchestration
    "full": "council_pipeline.py",
    "receipt-chain": "council_pipeline.py",
    "drift": "repo_sync.py",
    "record-fix": "repo_sync.py",
}


def _resolve_script(script: str) -> Path:
    """Find a script: same dir as council_entry.py first, then scripts/ subdir."""
    kit_path = KIT_DIR / script
    if kit_path.exists():
        return kit_path
    scripts_path = REPO_ROOT / "scripts" / script
    if scripts_path.exists():
        return scripts_path
    return REPO_ROOT / script

NEXUS_ARGS = {
    "sync": ["--path", "."],
    "read": None,       # requires positional file arg
    "diagnose-setup": ["--path", "."],
    "state-lineage": None,  # requires positional query arg
    "checkpoint": None,  # requires action arg
    "bench": None,  # requires cmd_a cmd_b
}

AEGIS_ARGS = {
    "hunt": ["--path", "."],
    "review": ["--base", "HEAD"],
    "forensics": None,  # requires target
    "dylib-audit": ["--path", "."],
    "cfg": None,  # requires binary
    "verify-fix": None,  # requires file
}

TOOL_LATENT_ARGS = {
    "run": None,  # requires command
    "deref": None,  # requires handle
    "bench-compression": [],
    "batch-compress": None,  # requires files
}


def _run_script(sub: str, script: str, extra: list[str]) -> int:
    """Run a script under arena_guard if available, otherwise directly.

    `sub` is the subcommand name (e.g. "sync") and is prepended to `extra`
    so the target script receives its subcommand as the first argument.
    """
    script_path = _resolve_script(script)
    if not script_path.exists():
        print(f"ERROR: Script not found: {script}", file=sys.stderr)
        return 2

    # The target script expects its subcommand as argv[1]
    script_args = [sub] + extra

    # Look for arena_guard in kit dir first, then scripts/ subdir
    arena_guard = KIT_DIR / "arena_guard.py"
    if not arena_guard.exists():
        arena_guard = REPO_ROOT / "scripts" / "arena_guard.py"

    if arena_guard.exists():
        cmd = [sys.executable, str(arena_guard), "exec", "--",
               sys.executable, str(script_path)] + script_args
    else:
        cmd = [sys.executable, str(script_path)] + script_args

    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    return proc.returncode


def show_help() -> None:
    print(__doc__)


def main() -> int:
    if len(sys.argv) < 2:
        show_help()
        return 1

    sub = sys.argv[1]
    extra = sys.argv[2:]

    if sub in ("help", "-h", "--help"):
        show_help()
        return 0

    if sub not in SCRIPT_MAP:
        print(f"ERROR: Unknown subcommand '{sub}'. Run 'council_entry.py help'.",
              file=sys.stderr)
        return 1

    script = SCRIPT_MAP[sub]
    return _run_script(sub, script, extra)


if __name__ == "__main__":
    sys.exit(main())
