#!/usr/bin/env python3
"""Deterministic local evidence capture and validation. Python 3 stdlib only.

Usage:
  python3 scripts/agent_receipt.py snapshot --out /tmp/agent-snapshot.json
  python3 scripts/agent_receipt.py verify path/to/gate-receipt.json
  python3 scripts/agent_receipt.py self-test
Never executes a build, device command, or network request.
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHA40 = re.compile(r"^[0-9a-f]{40}$")
STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
EVIDENCE = {"PROVEN_CODE", "TESTED_OFFLINE", "COMPILED", "MEASURED_DEVICE", "INFERRED", "PROPOSED", "UNKNOWN", "NOT_RUN"}

def git(*args):
    p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=False)
    if p.returncode:
        raise RuntimeError("git " + " ".join(args) + ": " + p.stderr.strip())
    return p.stdout.strip()

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def safe_path(rel):
    if not isinstance(rel, str) or not rel or pathlib.Path(rel).is_absolute():
        raise ValueError("evidence path must be a relative nonempty string")
    resolved = (ROOT / rel).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError("evidence path escapes repository")
    if not resolved.is_file():
        raise ValueError("evidence file missing: " + rel)
    return resolved

def validate(doc):
    errors = []
    if doc.get("schema") != "tv-agent/gate-receipt/v1":
        errors.append("wrong schema")
    for key in ("repo", "branch", "head_sha", "gate_id", "command", "status", "evidence_level"):
        if not isinstance(doc.get(key), str) or not doc[key]:
            errors.append("missing/invalid " + key)
    if not SHA40.fullmatch(doc.get("head_sha", "")):
        errors.append("head_sha must be full lowercase 40-hex")
    if doc.get("status") not in STATUSES:
        errors.append("invalid status")
    if doc.get("evidence_level") not in EVIDENCE:
        errors.append("invalid evidence_level")
    artifacts = doc.get("artifacts", [])
    if not isinstance(artifacts, list):
        errors.append("artifacts must be list")
        artifacts = []
    if doc.get("status") == "PASS" and not artifacts:
        errors.append("PASS requires at least one independently inspectable artifact")
    if doc.get("status") == "NOT_RUN" and doc.get("evidence_level") != "NOT_RUN":
        errors.append("NOT_RUN status must use NOT_RUN evidence level")
    for i, item in enumerate(artifacts):
        try:
            path = safe_path(item["path"])
            expected = item["sha256"]
            if not re.fullmatch(r"[0-9a-f]{64}", expected):
                raise ValueError("invalid sha256")
            if digest(path) != expected:
                raise ValueError("sha256 mismatch")
        except (KeyError, TypeError, ValueError) as exc:
            errors.append("artifact " + str(i) + ": " + str(exc))
    return errors

def snapshot(output):
    doc = {
        "schema": "tv-agent/snapshot/v1",
        "repo": ROOT.name,
        "branch": git("branch", "--show-current"),
        "head_sha": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "remotes": git("remote").splitlines(),
        "limits": {"offline_only": True, "device_mutations": False},
    }
    if output:
        pathlib.Path(output).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, indent=2))
    return 0

def self_test():
    fixture = {
        "schema":"tv-agent/gate-receipt/v1", "repo":"example",
        "branch":"test", "head_sha":"a"*40, "gate_id":"sample",
        "command":"not-run", "status":"NOT_RUN", "evidence_level":"NOT_RUN",
        "artifacts":[],
    }
    assert validate(fixture) == []
    fixture["status"] = "PASS"
    assert any("PASS requires" in e for e in validate(fixture))
    fixture["status"] = "NOT_RUN"
    fixture["head_sha"] = "bad"
    assert any("head_sha" in e for e in validate(fixture))
    print("agent_receipt self-test: PASS (3 vectors)")
    return 0

def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="cmd", required=True)
    snap = subs.add_parser("snapshot")
    snap.add_argument("--out")
    check = subs.add_parser("verify")
    check.add_argument("receipt")
    subs.add_parser("self-test")
    args = parser.parse_args()
    if args.cmd == "snapshot":
        return snapshot(args.out)
    if args.cmd == "self-test":
        return self_test()
    try:
        doc = json.loads(pathlib.Path(args.receipt).read_text(encoding="utf-8"))
        errors = validate(doc)
    except (OSError, ValueError, TypeError) as exc:
        errors = [str(exc)]
    for error in errors:
        print("FAIL: " + error, file=sys.stderr)
    if errors:
        return 1
    print("receipt verified: PASS")
    return 0

if __name__ == "__main__":
    sys.exit(main())
