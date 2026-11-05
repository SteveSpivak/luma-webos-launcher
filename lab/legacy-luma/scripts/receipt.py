#!/usr/bin/env python3
"""Run a deterministic command, retaining raw receipts outside the checkout.

No shell interpolation, dependency installation, network calls or device access.
Example: python3 research/scripts/receipt.py --out /home/user/luma-evidence \
  --label node-tests -- node --test tests/release.test.mjs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not argv or not args.label.replace("-", "").replace("_", "").isalnum():
        parser.error("A safe label and a command after -- are required")
    if args.timeout <= 0:
        parser.error("Timeout must be positive")
    cwd = args.cwd.resolve()
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=cwd, text=True).strip()).resolve()
    out = args.out.resolve()
    if out == root or root in out.parents:
        parser.error("Raw receipts must be outside the checkout")
    out.mkdir(parents=True, exist_ok=True)
    base = args.label
    stdout_path, stderr_path = out / f"{base}.stdout.log", out / f"{base}.stderr.log"
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    timed_out = False
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        try:
            result = subprocess.run(argv, cwd=cwd, stdout=stdout, stderr=stderr, shell=False, timeout=args.timeout, check=False)
            exit_code = result.returncode
        except FileNotFoundError:
            exit_code = 127
            stderr.write(f"Command unavailable: {argv[0]}\n".encode())
        except PermissionError:
            exit_code = 126
            stderr.write(f"Command not executable: {argv[0]}\n".encode())
        except OSError as error:
            exit_code = 127
            stderr.write(f"Command unavailable: {argv[0]} ({type(error).__name__})\n".encode())
        except subprocess.TimeoutExpired:
            exit_code = 124
            timed_out = True
            stderr.write(f"Receipt timeout after {args.timeout} seconds\n".encode())
    record = {
        "schema": "luma-command-receipt/1",
        "label": args.label,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.monotonic() - clock, 6),
        "cwd": str(cwd),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd, text=True).strip(),
        "argv": argv,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "execution_status": "TIMEOUT" if timed_out else ("BLOCKED" if exit_code in (126, 127) else ("PASS" if exit_code == 0 else "FAIL")),
        "evidence_scope": "host command only; not physical-TV evidence",
        "outputs": {p.name: {"sha256": sha256(p), "bytes": p.stat().st_size} for p in (stdout_path, stderr_path)},
    }
    receipt_path = out / f"{base}.json"
    receipt_path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"receipt": str(receipt_path), "exit_code": exit_code, "status": record["execution_status"], "stdout": str(stdout_path), "stderr": str(stderr_path)}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
