#!/usr/bin/env python3
"""Offline, standard-library-only agent context and evidence checks.

Commands:
  python3 scripts/agent_receipt.py snapshot [--out FILE] [--executor arena|local|chatgpt|ci]
  python3 scripts/agent_receipt.py verify RECEIPT.json
  python3 scripts/agent_receipt.py self-test

Does not probe GitHub, grant access, run remote tests or contact the TV.
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROFILE = ROOT / "docs" / "agent-profile.json"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
LEVELS = {"PROVEN_CODE", "TESTED_OFFLINE", "COMPILED", "MEASURED_DEVICE",
          "INFERRED", "PROPOSED", "UNKNOWN", "NOT_RUN"}
EXECUTORS = {"arena", "local", "chatgpt", "ci"}

def git(*args):
    p = subprocess.run(["git", "-C", str(ROOT), *args],
                       capture_output=True, text=True, check=False)
    if p.returncode:
        raise RuntimeError("git " + " ".join(args) + " failed: " + p.stderr.strip())
    return p.stdout.strip()

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(65536), b""):
            h.update(part)
    return h.hexdigest()

def artifact_path(name, root=ROOT):
    if not isinstance(name, str) or not name or pathlib.Path(name).is_absolute():
        raise ValueError("path must be relative and nonempty")
    path = root.joinpath(name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("path escapes repository or file is missing")
    return path

def validate(doc, root=ROOT):
    problems = []
    if not isinstance(doc, dict):
        return ["receipt must be a JSON object"]
    if doc.get("schema") != "tv-agent/gate-receipt/v1":
        problems.append("unsupported schema")
    for key in ("repo", "branch", "gate_id", "command"):
        if not isinstance(doc.get(key), str) or not doc[key].strip():
            problems.append("invalid " + key)
    if not isinstance(doc.get("head_sha"), str) or not SHA40.fullmatch(doc["head_sha"]):
        problems.append("head_sha must be a full 40-hex commit")
    if doc.get("status") not in STATUSES:
        problems.append("invalid status")
    if doc.get("evidence_level") not in LEVELS:
        problems.append("invalid evidence_level")
    exit_code = doc.get("exit_code")
    if exit_code is not None and (type(exit_code) is not int or exit_code < 0):
        problems.append("exit_code must be a nonnegative integer or null")
    artifacts = doc.get("artifacts", [])
    if not isinstance(artifacts, list):
        problems.append("artifacts must be a list")
        artifacts = []
    if doc.get("status") == "PASS":
        if not artifacts:
            problems.append("PASS requires an inspectable artifact")
        if exit_code != 0:
            problems.append("PASS requires exit_code=0")
        if doc.get("evidence_level") in {"UNKNOWN", "INFERRED", "PROPOSED", "NOT_RUN"}:
            problems.append("PASS requires executed or inspected evidence")
    if doc.get("status") == "NOT_RUN":
        if doc.get("evidence_level") != "NOT_RUN" or exit_code is not None:
            problems.append("NOT_RUN requires level NOT_RUN and exit_code null")
    if doc.get("status") == "BLOCKED" and not doc.get("blocker"):
        problems.append("BLOCKED requires blocker")
    seen = set()
    for i, entry in enumerate(artifacts):
        try:
            if not isinstance(entry, dict):
                raise ValueError("artifact must be object")
            p = artifact_path(entry["path"], root)
            if entry["path"] in seen:
                raise ValueError("duplicate artifact")
            seen.add(entry["path"])
            h = entry["sha256"]
            if not isinstance(h, str) or not SHA256.fullmatch(h):
                raise ValueError("invalid sha256")
            if sha256(p) != h:
                raise ValueError("sha256 mismatch")
        except (KeyError, ValueError, TypeError) as e:
            problems.append("artifact %d: %s" % (i, e))
    return problems

def snapshot(executor, output):
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    if profile.get("schema") != "tv-agent/repository-profile/v2":
        raise ValueError("profile schema mismatch")
    if executor not in EXECUTORS:
        raise ValueError("unsupported executor")
    actual_repo = profile["repo"]
    boundary = {
        "arena": "CURRENT_CHECKOUT_PLUS_AUTHORIZED_PUBLIC_DATA_ONLY",
        "local": "PRESENT_CHECKOUTS_AND_LOCALLY_AUTHORIZED_CREDENTIALS_ONLY",
        "chatgpt": "ACTIVE_CONNECTED_GITHUB_PERMISSIONS_ONLY",
        "ci": "EXPLICIT_RUNNER_CHECKOUT_AND_DEPENDENCIES_ONLY"
    }[executor]
    result = {
        "schema": "tv-agent/capability-snapshot/v2",
        "executor": executor,
        "repo": actual_repo,
        "branch": git("branch", "--show-current"),
        "head_sha": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "known_repo_visibility_at_review": profile["visibility_at_review"],
        "access": {"current_checkout": "READABLE", "other_repositories": "NOT_PROBED",
                   "network_permission": "NOT_PROBED", "scope": boundary},
        "owner_gated_actions": profile["dangerous_actions"],
        "device_access": "NOT_PROBED",
        "warning": "This is local observation, never an authorization grant or a remote access proof"
    }
    raw = json.dumps(result, indent=2) + "\n"
    if output:
        pathlib.Path(output).write_text(raw, encoding="utf-8")
    print(raw, end="")
    return 0

def self_test():
    with tempfile.TemporaryDirectory() as temp:
        root = pathlib.Path(temp)
        sample = root / "proof.txt"
        sample.write_text("known bytes\n", encoding="utf-8")
        fixture = {"schema": "tv-agent/gate-receipt/v1", "repo": "test/repo",
                   "branch": "test", "head_sha": "a" * 40, "gate_id": "G1",
                   "command": "python test.py", "status": "PASS",
                   "evidence_level": "TESTED_OFFLINE", "exit_code": 0,
                   "artifacts": [{"path": "proof.txt", "sha256": sha256(sample)}]}
        assert validate(fixture, root) == []
        fixture["artifacts"][0]["sha256"] = "0" * 64
        assert any("sha256 mismatch" in s for s in validate(fixture, root))
        fixture["artifacts"][0]["sha256"] = sha256(sample)
        fixture["status"] = "NOT_RUN"
        assert validate(fixture, root)
        fixture["evidence_level"], fixture["exit_code"] = "NOT_RUN", None
        assert validate(fixture, root) == []
        fixture["status"], fixture["evidence_level"], fixture["exit_code"] = "BLOCKED", "UNKNOWN", None
        assert validate(fixture, root)
        fixture["blocker"] = "REPOSITORY_ACCESS_DENIED"
        assert validate(fixture, root) == []
        fixture["status"], fixture["evidence_level"], fixture["exit_code"] = "PASS", "TESTED_OFFLINE", 0
        fixture["artifacts"][0]["path"] = "../proof.txt"
        assert validate(fixture, root)
        assert validate([], root)
    print("agent_receipt self-test: PASS (8 assertions, positive and mutation cases)")
    return 0

def main():
    ap = argparse.ArgumentParser()
    subs = ap.add_subparsers(dest="action", required=True)
    p = subs.add_parser("snapshot")
    p.add_argument("--out")
    p.add_argument("--executor", choices=sorted(EXECUTORS), default="local")
    p = subs.add_parser("verify")
    p.add_argument("receipt")
    subs.add_parser("self-test")
    args = ap.parse_args()
    try:
        if args.action == "self-test":
            return self_test()
        if args.action == "snapshot":
            return snapshot(args.executor, args.out)
        problems = validate(json.loads(pathlib.Path(args.receipt).read_text(encoding="utf-8")))
        if problems:
            for problem in problems:
                print("FAIL:", problem, file=sys.stderr)
            return 1
        print("receipt verified: PASS (schema + local file hashes; NOT test execution)")
        return 0
    except (OSError, ValueError, RuntimeError) as e:
        print("FAIL:", e, file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
