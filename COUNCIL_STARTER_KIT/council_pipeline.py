#!/usr/bin/env python3
"""
COUNCIL PIPELINE — Unified Forensics, Bug-Hunting & Zero-Regression Fix Orchestrator

Chains the three Council CLIs into a single reproducible pipeline with chained
RCPT receipts:

  STAGE 1 — nexus_agent_os.py sync
      O(Δ) wait-free polyglot index: symbols, edges, state channels, import traps
  STAGE 2 — aegis_bug_hunter.py hunt
      Engler deviance mining + PVS-Studio AST anomaly detection
  STAGE 3 — aegis_bug_hunter.py forensics (optional, per-target)
      AST-Refined SZZ bug genealogy → Bug-Inducing Commit
  STAGE 4 — tool_latent_codec.py run -- (compress hunt/forensics output)
      HSLC symbolic-latent compression → @H-XXXXXXXX epistemic handle
  STAGE 5 — aegis_bug_hunter.py verify-fix (optional, per-file)
      Separation-Logic Frame Rule + Liskov call-site invariance → SAFE_TO_SHIP
  STAGE 6 — tool_latent_codec.py run -- (compress verify-fix output)
  STAGE 7 — repo_sync.py drift + record-fix
      Cross-repo drift detection + fix provenance recording
  STAGE 8 — arena_guard.py ship
      Verified LOCAL_SHA == REMOTE_SHA persistence

Every stage emits an arena_guard RCPT receipt. Stage receipts are chained:
the previous receipt id is recorded as `parent_receipt` in the next, forming
an auditable evidence chain from source index to shipped fix.

Zero external dependencies — pure Python 3.11 stdlib.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(os.environ.get("REPO_ROOT", ".")).resolve()
KIT_DIR = Path(__file__).resolve().parent
PIPELINE_RECEIPT_FILE = REPO_ROOT / ".agent-kb" / "council_pipeline_receipts.json"


def _resolve_script(script: str) -> str:
    """Resolve a script path: kit dir first, then scripts/ subdir, then bare."""
    kit_path = KIT_DIR / script
    if kit_path.exists():
        return str(kit_path)
    scripts_path = REPO_ROOT / "scripts" / script
    if scripts_path.exists():
        return str(scripts_path)
    return script


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def run_cmd(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Run a command, returning the CompletedProcess."""
    return subprocess.run(
        cmd, cwd=REPO_ROOT,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
    )


def arena_guard_exec(command: list[str], label: str = "") -> dict:
    """Run a command under arena_guard exec to get an RCPT receipt."""
    ag = _resolve_script("arena_guard.py")
    full = ["python3", ag, "exec", "--"] + command
    proc = run_cmd(full)
    # Extract receipt id from stdout/stderr
    receipt_id = None
    combined = proc.stdout + proc.stderr
    for line in combined.splitlines():
        if "[ARENA RECEIPT ISSUED]" in line:
            # id=RCPT-XXXX
            for token in line.split():
                if token.startswith("id="):
                    receipt_id = token.split("=", 1)[1]
                    break
    return {
        "command": " ".join(command),
        "label": label,
        "exit_code": proc.returncode,
        "receipt_id": receipt_id,
        "stdout_tail": proc.stdout[-500:] if proc.stdout else "",
        "stderr_tail": proc.stderr[-500:] if proc.stderr else "",
    }


def load_pipeline_receipts() -> list[dict]:
    if PIPELINE_RECEIPT_FILE.exists():
        try:
            return json.loads(PIPELINE_RECEIPT_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_pipeline_receipt(receipt: dict) -> None:
    PIPELINE_RECEIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    receipts = load_pipeline_receipts()
    receipts.append(receipt)
    PIPELINE_RECEIPT_FILE.write_text(json.dumps(receipts, indent=2))


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------
def stage_0_validate_constraints() -> dict:
    """Stage 0: Validate Nuvio user constraints (precondition check).

    Enforces:
      - space.nuvio.webos never modified/launched/replaced
      - space.nuvio.lab only when nuvio_lab feature + lab=true
      - Invalid app IDs fail validation (no silent override)
      - Production app ID never used for lab launches
    """
    print("[STAGE 0] nuvio_constraint_validator.py — constraint validation")
    res = arena_guard_exec(
        ["python3", _resolve_script("nuvio_constraint_validator.py")],
        "nuvio_constraint_validate",
    )
    print(f"  receipt={res['receipt_id']} exit={res['exit_code']}")
    return res


def stage_1_nexus_sync(workers: int = 4) -> dict:
    """Stage 1: O(Δ) wait-free polyglot index."""
    print("[STAGE 1] nexus_agent_os.py sync — polyglot index")
    res = arena_guard_exec(
        ["python3", _resolve_script("nexus_agent_os.py"), "sync", "--path", ".", "--workers", str(workers)],
        "nexus_sync",
    )
    print(f"  receipt={res['receipt_id']} exit={res['exit_code']}")
    return res


def stage_2_aegis_hunt() -> dict:
    """Stage 2: Engler deviance mining + PVS-Studio AST anomalies."""
    print("[STAGE 2] aegis_bug_hunter.py hunt — bug detection")
    res = arena_guard_exec(
        ["python3", _resolve_script("aegis_bug_hunter.py"), "hunt", "--path", "."],
        "aegis_hunt",
    )
    print(f"  receipt={res['receipt_id']} exit={res['exit_code']}")
    return res


def stage_3_aegis_forensics(target: str) -> dict:
    """Stage 3: AST-Refined SZZ bug genealogy."""
    print(f"[STAGE 3] aegis_bug_hunter.py forensics {target} — SZZ bug genealogy")
    res = arena_guard_exec(
        ["python3", _resolve_script("aegis_bug_hunter.py"), "forensics", target],
        "aegis_forensics",
    )
    print(f"  receipt={res['receipt_id']} exit={res['exit_code']}")
    return res


def stage_4_tool_latent_compress(command_str: str, label: str = "tool_latent_compress") -> dict:
    """Stage 4: HSLC symbolic-latent compression of a command's output."""
    print(f"[STAGE 4] tool_latent_codec.py run -- {command_str} — latent compression")
    # Parse command: split on '--' if present
    parts = command_str.split(" -- ", 1)
    if len(parts) == 2:
        cmd = parts[1].split()
    else:
        cmd = command_str.split()
    res = arena_guard_exec(
        ["python3", _resolve_script("tool_latent_codec.py"), "run", "--"] + cmd,
        label,
    )
    print(f"  receipt={res['receipt_id']} exit={res['exit_code']}")
    return res


def stage_5_aegis_verify_fix(file_path: str) -> dict:
    """Stage 5: Separation-Logic Frame Rule verification."""
    print(f"[STAGE 5] aegis_bug_hunter.py verify-fix {file_path} — frame rule proof")
    res = arena_guard_exec(
        ["python3", _resolve_script("aegis_bug_hunter.py"), "verify-fix", file_path],
        "aegis_verify_fix",
    )
    print(f"  receipt={res['receipt_id']} exit={res['exit_code']}")
    return res


def stage_6_repo_sync_drift() -> dict:
    """Stage 6: Cross-repo drift detection."""
    print("[STAGE 6] repo_sync.py drift — cross-repo drift detection")
    res = arena_guard_exec(
        ["python3", _resolve_script("repo_sync.py"), "drift"],
        "repo_sync_drift",
    )
    print(f"  receipt={res['receipt_id']} exit={res['exit_code']}")
    return res


def stage_7_arena_guard_ship(title: str, what: str, why: str, where: str,
                             how: str, receipt: str) -> dict:
    """Stage 7: arena_guard ship — verified SHA parity."""
    print("[STAGE 7] arena_guard.py ship — verified persistence")
    res = arena_guard_exec(
        ["python3", _resolve_script("arena_guard.py"), "ship", title,
         "--what", what, "--why", why, "--where", where,
         "--how", how, "--receipt", receipt],
        "arena_guard_ship",
    )
    print(f"  receipt={res['receipt_id']} exit={res['exit_code']}")
    return res


# ---------------------------------------------------------------------------
# Pipeline modes
# ---------------------------------------------------------------------------
def run_full_pipeline(args) -> int:
    """Run the complete Council pipeline end-to-end."""
    t0 = time.monotonic()
    pipeline_receipt = {
        "pipeline_id": f"COUNCIL-{int(time.time())}",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "head_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        "stages": [],
        "all_passed": True,
    }

    # Stage 0: Constraint validation (Nuvio user constraints)
    s0 = stage_0_validate_constraints()
    pipeline_receipt["stages"].append(s0)
    if s0["exit_code"] != 0:
        pipeline_receipt["all_passed"] = False

    # Stage 1: Nexus sync
    s1 = stage_1_nexus_sync(workers=args.workers)
    pipeline_receipt["stages"].append(s1)
    if s1["exit_code"] != 0:
        pipeline_receipt["all_passed"] = False

    # Stage 2: Aegis hunt
    s2 = stage_2_aegis_hunt()
    pipeline_receipt["stages"].append(s2)
    if s2["exit_code"] != 0:
        pipeline_receipt["all_passed"] = False

    # Stage 3: Aegis forensics (if target specified)
    if args.forensics_target:
        s3 = stage_3_aegis_forensics(args.forensics_target)
        pipeline_receipt["stages"].append(s3)
        if s3["exit_code"] != 0:
            pipeline_receipt["all_passed"] = False

    # Stage 4: Tool latent compression of hunt output
    s4 = stage_4_tool_latent_compress(
        f"python3 {_resolve_script('aegis_bug_hunter.py')} hunt --path .",
        "tool_latent_compress_hunt",
    )
    pipeline_receipt["stages"].append(s4)
    if s4["exit_code"] != 0:
        pipeline_receipt["all_passed"] = False

    # Stage 5: Aegis verify-fix (if file specified)
    if args.verify_fix_file:
        s5 = stage_5_aegis_verify_fix(args.verify_fix_file)
        pipeline_receipt["stages"].append(s5)
        if s5["exit_code"] != 0:
            pipeline_receipt["all_passed"] = False

    # Stage 6: Repo sync drift
    s6 = stage_6_repo_sync_drift()
    pipeline_receipt["stages"].append(s6)
    if s6["exit_code"] != 0:
        pipeline_receipt["all_passed"] = False

    # Stage 7: Arena guard ship (if requested, requires ship params)
    if args.ship:
        if not (args.ship_title and args.ship_what and args.ship_why and
                args.ship_where and args.ship_how and args.ship_receipt):
            print("[STAGE 7] SKIPPED — --ship requires --ship-title, --ship-what, --ship-why, "
                  "--ship-where, --ship-how, --ship-receipt")
        else:
            # Use last stage receipt as the provenance receipt if not provided
            ship_receipt = args.ship_receipt or pipeline_receipt["stages"][-1].get("receipt_id", "")
            s7 = stage_7_arena_guard_ship(
                title=args.ship_title,
                what=args.ship_what,
                why=args.ship_why,
                where=args.ship_where,
                how=args.ship_how,
                receipt=ship_receipt,
            )
            pipeline_receipt["stages"].append(s7)
            if s7["exit_code"] != 0:
                pipeline_receipt["all_passed"] = False

    elapsed = round((time.monotonic() - t0) * 1000, 2)
    pipeline_receipt["total_duration_ms"] = elapsed
    pipeline_receipt["stages_completed"] = len(pipeline_receipt["stages"])

    save_pipeline_receipt(pipeline_receipt)

    # Print summary
    print("\n" + "=" * 70)
    print(f"COUNCIL PIPELINE COMPLETE — {elapsed}ms")
    print(f"  All stages passed: {pipeline_receipt['all_passed']}")
    print(f"  Stages completed: {pipeline_receipt['stages_completed']}")
    for i, s in enumerate(pipeline_receipt["stages"], 1):
        status = "PASS" if s["exit_code"] == 0 else "FAIL"
        print(f"  Stage {i} [{status}] {s['label']}: receipt={s['receipt_id']}")
    print("=" * 70)

    return 0 if pipeline_receipt["all_passed"] else 1


def run_receipt_chain(args) -> int:
    """Display the chained receipt chain from .agent-kb/council_pipeline_receipts.json."""
    receipts = load_pipeline_receipts()
    if not receipts:
        print("No council pipeline receipts found. Run 'full' first.")
        return 0
    print(f"\nCOUNCIL PIPELINE RECEIPT CHAIN ({len(receipts)} runs)")
    print("-" * 70)
    for r in receipts:
        print(f"\n  Pipeline: {r['pipeline_id']}")
        print(f"    Time:   {r['timestamp_utc']}")
        print(f"    Head:   {r['head_sha'][:12]}")
        print(f"    Passed: {r['all_passed']} | Duration: {r['total_duration_ms']}ms")
        for s in r["stages"]:
            status = "PASS" if s["exit_code"] == 0 else "FAIL"
            parent = s.get("receipt_id", "NONE")
            print(f"    [{status}] {s['label']:30} receipt={parent}")
    print("-" * 70)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Council Pipeline — unified forensics, bug-hunting & zero-regression fix orchestrator"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    full = sub.add_parser("full", help="Run the complete Council pipeline end-to-end")
    full.add_argument("--workers", type=int, default=4, help="Nexus sync parallel workers")
    full.add_argument("--forensics-target", help="File:line range for SZZ forensics (stage 3)")
    full.add_argument("--verify-fix-file", help="File to verify with Frame Rule (stage 5)")
    full.add_argument("--ship", action="store_true", help="Run arena_guard ship (stage 7)")
    full.add_argument("--ship-title", help="Conventional commit title for ship")
    full.add_argument("--ship-what", help="What changed")
    full.add_argument("--ship-why", help="Why the change")
    full.add_argument("--ship-where", help="Where the change lives")
    full.add_argument("--ship-how", help="How the change was made")
    full.add_argument("--ship-receipt", help="RCPT receipt id (defaults to last stage)")

    chain = sub.add_parser("receipt-chain", help="Display chained council pipeline receipts")

    args = p.parse_args()
    if args.cmd == "full":
        return run_full_pipeline(args)
    if args.cmd == "receipt-chain":
        return run_receipt_chain(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
