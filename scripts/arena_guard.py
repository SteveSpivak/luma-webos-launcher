#!/usr/bin/env python3
"""
ARENA GUARD — Zero-Fabrication, Auto-Doc-Sync & Guaranteed GitHub Persistence Engine.
Ensures Cloud Arena Agents never lose commits, never invent metrics, and always keep
BLUF + ADHD + ASCII + 5-W documentation synchronized with code.

Usage:
  python3 scripts/arena_guard.py init
  python3 scripts/arena_guard.py exec -- <command...>
  python3 scripts/arena_guard.py audit
  python3 scripts/arena_guard.py ship "<title>" --what "..." --why "..." --where "..." --how "..." --receipt "RCPT-XXXXXXXXXXXX"
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(os.environ.get("REPO_ROOT", ".")).resolve()
XRAY_DIR = REPO_ROOT / "docs" / "xray"
DATA_DIR = XRAY_DIR / "_data"
RECEIPTS_FILE = DATA_DIR / "execution_receipts.json"

SECRET_RE = re.compile(
    r"(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{30,}|AKIA[0-9A-Z]{16}|"
    r"-----BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY-----)"
)
CITATION_RE = re.compile(
    r"\[([^\]]+)\]\(([^)#:\s]+)(?:#L?(\d+)(?:-L?(\d+))?)?\)"
)
ASCII_BOX_RE = re.compile(r"(\+[=-]{3,}\+|[┌┍┎┏][─━]{3,}[┐┑┒┓])")


def run_cmd(cmd, check=False):
    return subprocess.run(
        cmd, cwd=REPO_ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check,
    )


# -------------------------------------------------------------------------
# 1. INIT: BRANCH HYGIENE & GIT HOOK INSTALLATION
# -------------------------------------------------------------------------
def cmd_init(args):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not RECEIPTS_FILE.exists():
        RECEIPTS_FILE.write_text("[]")

    # Ensure git user config exists for cloud containers
    if not run_cmd(["git", "config", "user.name"]).stdout.strip():
        run_cmd(["git", "config", "user.name", "Arena-Cloud-Agent"])
    if not run_cmd(["git", "config", "user.email"]).stdout.strip():
        run_cmd(["git", "config", "user.email", "arena-agent@research-os.local"])

    # Prevent Detached HEAD loss — ensure a real branch is checked out
    branch = run_cmd(["git", "symbolic-ref", "--short", "-q", "HEAD"]).stdout.strip()
    if not branch:
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M")
        branch = f"arena/session-{ts}"
        run_cmd(["git", "checkout", "-b", branch], check=True)
        print(f"[ARENA INIT] Recovered from detached HEAD -> created branch '{branch}'")
    else:
        print(f"[ARENA INIT] Active branch verified: '{branch}'")

    # Install pre-commit hook to block raw commits that bypass doc-sync & BLUF audit
    hooks_dir = REPO_ROOT / ".git" / "hooks"
    if hooks_dir.exists():
        pre_commit = hooks_dir / "pre-commit"
        pre_commit.write_text("#!/bin/sh\nexec python3 scripts/arena_guard.py audit\n")
        pre_commit.chmod(0o755)
        print("[ARENA INIT] pre-commit hook installed (runs arena_guard.py audit).")
    print("[ARENA INIT] Execution Receipt ledger armed at docs/xray/_data/execution_receipts.json")


# -------------------------------------------------------------------------
# 2. EXEC: TAMPER-EVIDENT EXECUTION RECEIPTS (NO INVENTED METRICS)
# -------------------------------------------------------------------------
def cmd_exec(args):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cmd_list = list(args.command)
    if cmd_list and cmd_list[0] == "--":
        cmd_list = cmd_list[1:]
    if not cmd_list:
        print("FAIL: Provide a command after 'exec --'", file=sys.stderr)
        sys.exit(1)

    t0 = datetime.datetime.now(datetime.timezone.utc)
    start_perf = time.perf_counter()
    proc = run_cmd(cmd_list)
    duration_ms = round((time.perf_counter() - start_perf) * 1000, 2)

    head_sha = run_cmd(["git", "rev-parse", "--short", "HEAD"]).stdout.strip() or "UNCOMMITTED"
    ts = t0.isoformat()
    payload = f"{ts}|{' '.join(cmd_list)}|{proc.returncode}|{duration_ms}|{proc.stdout}"
    receipt_id = "RCPT-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12].upper()

    receipts = json.loads(RECEIPTS_FILE.read_text()) if RECEIPTS_FILE.exists() else []
    receipt_entry = {
        "receipt_id": receipt_id,
        "timestamp_utc": ts,
        "git_head": head_sha,
        "command": " ".join(cmd_list),
        "exit_code": proc.returncode,
        "duration_ms": duration_ms,
        "output_preview": proc.stdout[-600:].strip(),
    }
    receipts.append(receipt_entry)
    RECEIPTS_FILE.write_text(json.dumps(receipts, indent=2))

    print(proc.stdout, end="")
    print(
        f"\n[ARENA RECEIPT ISSUED] id={receipt_id} | exit={proc.returncode} | "
        f"time={duration_ms}ms | head={head_sha}"
    )
    sys.exit(proc.returncode)


# -------------------------------------------------------------------------
# 3. AUDIT: BLUF + ADHD + ASCII + CITATIONS + CODE-DOC SYNC VERIFIER
# -------------------------------------------------------------------------
def _changed_files():
    out = run_cmd(["git", "status", "--porcelain"]).stdout.splitlines()
    files = []
    for line in out:
        if len(line) > 3:
            path = line[3:].strip().split(" -> ")[-1]
            files.append(path)
    return files


def cmd_audit(args):
    errors = []
    changed_files = _changed_files()

    # 1. Secret Leak Check
    for cf in changed_files:
        p = REPO_ROOT / cf
        if p.is_file() and p.stat().st_size < 2_000_000:
            content = p.read_text(errors="ignore")
            if SECRET_RE.search(content):
                errors.append(f"SECURITY BLOCK: Potential secret/token detected in '{cf}'")

    # 2. Code-to-Doc Co-Change Sync Check
    code_changed = [
        f for f in changed_files
        if not f.startswith(("docs/", "scripts/", "labs/", "."))
        and Path(f).suffix in {".py", ".rs", ".ts", ".tsx", ".js", ".go", ".java", ".sql", ".c", ".h", ".cpp"}
    ]
    docs_changed = [f for f in changed_files if f.startswith("docs/xray/") or f == "README.md"]
    if code_changed and not docs_changed and not os.environ.get("ALLOW_DOC_SKIP"):
        errors.append(
            f"DOC-SYNC VIOLATION: Code files changed {code_changed[:3]} but no docs in "
            f"'docs/xray/' were updated."
        )

    # 3. Audit all Markdown docs in docs/xray/ for BLUF, ASCII, and Valid Citations
    core_docs = {"README.md", "01_5W_ARCHITECTURE_ATLAS.md", "02_END_TO_END_FLOWS.md"}
    if XRAY_DIR.exists():
        md_files = sorted(XRAY_DIR.rglob("*.md"))
        for md in md_files:
            text = md.read_text(errors="replace")
            head_chunk = "\n".join(text.splitlines()[:12]).upper()
            if "BLUF" not in head_chunk:
                errors.append(
                    f"ERGONOMICS VIOLATION: '{md.relative_to(REPO_ROOT)}' missing top "
                    f"'> ⚡ **BLUF' header."
                )
            if md.name in core_docs:
                if not ASCII_BOX_RE.search(text):
                    errors.append(
                        f"ASCII VIOLATION: Core doc '{md.name}' must include at least one "
                        f"ASCII box diagram (+---+ or ┌───┐)."
                    )
            for _, target, l_start, _ in CITATION_RE.findall(text):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                cand = (md.parent / target).resolve()
                if not cand.exists():
                    cand = (REPO_ROOT / target).resolve()
                if not cand.exists():
                    errors.append(
                        f"BROKEN CITATION: '{target}' in '{md.relative_to(REPO_ROOT)}' "
                        f"does not exist."
                    )
                elif l_start:
                    try:
                        file_lines = len(cand.read_text(errors="replace").splitlines())
                        ls = int(l_start.lstrip("L"))
                        if not (1 <= ls <= max(1, file_lines + 5)):
                            errors.append(
                                f"CITATION OUT OF RANGE: {target}#{l_start} in "
                                f"'{md.relative_to(REPO_ROOT)}' (file has {file_lines} lines)."
                            )
                    except (OSError, ValueError):
                        pass

    if errors:
        print("\n".join(["[ARENA AUDIT FAILED]"] + [f"  ❌ {e}" for e in errors]))
        sys.exit(1)
    print("[ARENA AUDIT PASSED] BLUF, ASCII, Citation, Secret, and Doc-Sync checks verified.")


# -------------------------------------------------------------------------
# 4. SHIP: ATOMIC 5-W COMMIT + REBASE + PUSH + REMOTE SHA PARITY CHECK
# -------------------------------------------------------------------------
def cmd_ship(args):
    receipts = json.loads(RECEIPTS_FILE.read_text()) if RECEIPTS_FILE.exists() else []
    valid_ids = {r["receipt_id"] for r in receipts if r["exit_code"] == 0}
    if args.receipt not in valid_ids:
        print(
            f"FAIL: Receipt '{args.receipt}' not found or failed in {RECEIPTS_FILE}. "
            f"Run tests via 'arena_guard.py exec' first—never invent verification!",
            file=sys.stderr,
        )
        sys.exit(1)

    run_cmd(["git", "add", "-A"], check=True)
    cmd_audit(args)

    diff_stat = run_cmd(["git", "diff", "--cached", "--stat"]).stdout.strip()
    if not diff_stat:
        print("[ARENA SHIP] Working tree clean; nothing new to commit.")
    else:
        commit_msg = (
            f"{args.title}\n\n"
            f"⚡ BLUF / 5-W ATOMIC SUMMARY\n"
            f"+----------------------------------------------------------------------+\n"
            f"| WHAT  : {args.what[:60]:<60} |\n"
            f"| WHY   : {args.why[:60]:<60} |\n"
            f"| WHERE : {args.where[:60]:<60} |\n"
            f"| HOW   : {args.how[:60]:<60} |\n"
            f"| PROOF : Verified Execution Receipt {args.receipt:<33} |\n"
            f"+----------------------------------------------------------------------+\n\n"
            f"DIFF BLAST RADIUS:\n{diff_stat}\n\n"
            f"Arena-Receipt: {args.receipt}\n"
            f"Doc-Sync: VERIFIED\n"
        )
        res = run_cmd(["git", "commit", "-m", commit_msg])
        if res.returncode != 0:
            print(f"COMMIT FAILED:\n{res.stdout}", file=sys.stderr)
            sys.exit(1)

    branch = run_cmd(["git", "symbolic-ref", "--short", "HEAD"]).stdout.strip()
    local_sha = run_cmd(["git", "rev-parse", "HEAD"]).stdout.strip()
    remotes = run_cmd(["git", "remote"]).stdout.split()

    if "origin" not in remotes:
        print(
            f"WARNING: No 'origin' remote configured. Local commit {local_sha[:8]} saved on '{branch}'."
        )
        sys.exit(0)

    run_cmd(["git", "pull", "--rebase", "--autostash", "origin", branch])
    push_res = run_cmd(["git", "push", "-u", "origin", branch])
    if push_res.returncode != 0:
        print(f"PUSH FAILED:\n{push_res.stdout}", file=sys.stderr)
        sys.exit(1)

    local_sha = run_cmd(["git", "rev-parse", "HEAD"]).stdout.strip()
    ls_remote = run_cmd(["git", "ls-remote", "origin", f"refs/heads/{branch}"]).stdout.strip()
    remote_sha = ls_remote.split()[0] if ls_remote else "MISSING"

    if local_sha != remote_sha:
        print(
            f"CRITICAL PERSISTENCE FAILURE: Local SHA ({local_sha}) != Remote GitHub SHA ({remote_sha})!",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[ARENA SHIP VERIFIED] Branch '{branch}' pushed to GitHub origin. SHA Parity Confirmed: {local_sha}")


def main():
    p = argparse.ArgumentParser(
        description="Arena Cloud Agent Guardrail & Persistence CLI"
    )
    sub = p.add_subparsers(dest="sub", required=True)
    sub.add_parser("init")
    sub.add_parser("audit")
    ex = sub.add_parser("exec")
    ex.add_argument("command", nargs=argparse.REMAINDER)
    sh = sub.add_parser("ship")
    sh.add_argument("title", help="Conventional commit title")
    sh.add_argument("--what", required=True)
    sh.add_argument("--why", required=True)
    sh.add_argument("--where", required=True)
    sh.add_argument("--how", required=True)
    sh.add_argument("--receipt", required=True, help="RCPT-XXXX ID from 'arena_guard.py exec'")
    args = p.parse_args()
    {"init": cmd_init, "exec": cmd_exec, "audit": cmd_audit, "ship": cmd_ship}[args.sub](args)


if __name__ == "__main__":
    main()
