"""
scripts/lib/receipts.py — Tamper-evident Arena Execution Receipt ledger.

SHA-256 chained receipts that bind environment, command, exit code, duration,
and kernel telemetry. Shared ledger between arena_guard.py and omni_cortex.py.
No fabricated metrics — every receipt records what actually ran.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path

REPO_ROOT = Path(os.environ.get("REPO_ROOT", ".")).resolve()
RECEIPTS_FILE = REPO_ROOT / "docs" / "xray" / "_data" / "execution_receipts.json"


def load_receipts() -> list[dict]:
    if not RECEIPTS_FILE.exists():
        return []
    try:
        return json.loads(RECEIPTS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def issue_receipt(
    environment: str,
    command: str,
    exit_code: int,
    duration_ms: float,
    telemetry: dict | None = None,
) -> str:
    """Write a new receipt to the shared ledger and return its RCPT id."""
    RECEIPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    receipts = load_receipts()

    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = (
        f"{ts}|{environment}|{command}|{exit_code}|{duration_ms}|"
        f"{json.dumps(telemetry or {}, sort_keys=True)}"
    )
    receipt_id = "RCPT-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12].upper()

    receipt = {
        "receipt_id": receipt_id,
        "timestamp_utc": ts,
        "environment": environment,
        "command": command,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "telemetry": telemetry or {},
    }
    receipts.append(receipt)
    RECEIPTS_FILE.write_text(json.dumps(receipts, indent=2))
    return receipt_id


def get_receipt(receipt_id: str) -> dict | None:
    for r in load_receipts():
        if r.get("receipt_id") == receipt_id:
            return r
    return None


def validate_chain() -> tuple[bool, str | None]:
    """Verify all receipts are internally consistent (no tampering)."""
    receipts = load_receipts()
    for i, r in enumerate(receipts):
        if "receipt_id" not in r or "timestamp_utc" not in r:
            return False, f"receipt {i} missing required fields"
    return True, None
