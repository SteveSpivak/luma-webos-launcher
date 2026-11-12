#!/usr/bin/env python3
"""
Starter Kit Self-Test

Verifies that all Council CLI scripts parse, run, and exit 0 in a fresh repo.
Run with: python3 tests/test_starter_kit.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    "council_entry.py",
    "nexus_agent_os.py",
    "tool_latent_codec.py",
    "aegis_bug_hunter.py",
    "council_pipeline.py",
    "arena_guard.py",
    "repo_sync.py",
]

FAILURES = []


def run(cmd, cwd=None, timeout=60):
    """Run a command, return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        cmd, cwd=cwd or REPO_ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _extract_json_from_output(out):
    """Extract a JSON object from command output that may have receipt lines."""
    lines = out.strip().split("\n")

    # Try each line individually (single-line JSON)
    for l in lines:
        l = l.strip()
        if not l:
            continue
        try:
            return json.loads(l), None
        except json.JSONDecodeError:
            continue

    # Try accumulating lines starting from the first '{' line (pretty-printed JSON)
    brace_starts = [i for i, l in enumerate(lines) if l.lstrip().startswith("{")]
    for start in brace_starts:
        for end in range(start + 1, len(lines) + 1):
            candidate = "\n".join(lines[start:end])
            try:
                return json.loads(candidate), None
            except json.JSONDecodeError:
                continue

    # Try accumulating lines from the start (fallback)
    for end in range(len(lines), 0, -1):
        candidate = "\n".join(lines[:end])
        try:
            return json.loads(candidate), None
        except json.JSONDecodeError:
            continue

    return None, "No valid JSON in output"


def test_script_parses(script):
    """Verify a Python script parses without syntax errors."""
    path = REPO_ROOT / script
    try:
        compile(path.read_text(), str(path), "exec")
        return True, None
    except SyntaxError as e:
        return False, str(e)


def test_council_entry_help():
    """council_entry.py help should exit 0."""
    rc, out, err = run(["python3", "council_entry.py", "help"])
    return rc == 0, f"rc={rc}, err={err[:200]}" if rc != 0 else None


def test_nexus_sync():
    """nexus sync should exit 0 and produce JSON."""
    rc, out, err = run(["python3", "council_entry.py", "sync", "--path", ".", "--workers", "2"])
    if rc != 0:
        return False, f"rc={rc}, err={err[:200]}"
    d, err = _extract_json_from_output(out)
    if d is None:
        return False, err
    if "total_files" not in d:
        return False, "JSON missing total_files field"
    return True, None


def test_aegis_hunt():
    """aegis hunt should exit 0 and produce JSON with anomaly count."""
    rc, out, err = run(["python3", "council_entry.py", "hunt", "--path", "."])
    if rc != 0:
        return False, f"rc={rc}, err={err[:200]}"
    d, err = _extract_json_from_output(out)
    if d is None:
        return False, err
    if "total_anomalies_found" not in d:
        return False, "JSON missing total_anomalies_found field"
    return True, None


def test_aegis_dylib_audit():
    """aegis dylib-audit should exit 0 (may find 0 binaries)."""
    rc, out, err = run(["python3", "council_entry.py", "dylib-audit"])
    return rc == 0, f"rc={rc}" if rc != 0 else None


def test_aegis_cfg():
    """aegis cfg should exit 0 on /bin/true if objdump available."""
    import shutil
    if not shutil.which("objdump"):
        return None, "objdump not available — skipping"
    rc, out, err = run(["python3", "council_entry.py", "cfg", "/bin/true"])
    return rc == 0, f"rc={rc}, err={err[:200]}" if rc != 0 else None


def test_tool_latent_bench():
    """tool_latent_codec bench-compression should exit 0."""
    rc, out, err = run(["python3", "council_entry.py", "bench-compression"])
    if rc != 0:
        return False, f"rc={rc}, err={err[:200]}"
    d, err = _extract_json_from_output(out)
    if d is None:
        return False, err
    if "token_compression_ratio_x" not in d:
        return False, "JSON missing token_compression_ratio_x field"
    return True, None


def test_council_pipeline_full():
    """council_entry.py full should exit 0 with all stages passing."""
    rc, out, err = run(
        ["python3", "council_entry.py", "full", "--workers", "2"],
        timeout=120,
    )
    if rc != 0:
        return False, f"rc={rc}, err={err[:200]}"
    if "All stages passed: True" not in out:
        return False, "Pipeline did not report all stages passed"
    return True, None


def main():
    print("=== Council Starter Kit Self-Test ===\n")

    # 1. All scripts parse
    print("1. Script parse check...")
    for script in SCRIPTS:
        ok, err = test_script_parses(script)
        status = "PASS" if ok else "FAIL"
        print(f"   {script}: {status}" + (f" — {err}" if err else ""))
        if not ok:
            FAILURES.append(f"{script} parse: {err}")

    # 2. council_entry help
    print("\n2. council_entry help...")
    ok, err = test_council_entry_help()
    print(f"   council_entry help: {'PASS' if ok else 'FAIL'} {err or ''}")
    if not ok:
        FAILURES.append(f"council_entry help: {err}")

    # 3. nexus sync
    print("\n3. nexus sync...")
    ok, err = test_nexus_sync()
    print(f"   nexus sync: {'PASS' if ok else 'FAIL'} {err or ''}")
    if not ok:
        FAILURES.append(f"nexus sync: {err}")

    # 4. aegis hunt
    print("\n4. aegis hunt...")
    ok, err = test_aegis_hunt()
    print(f"   aegis hunt: {'PASS' if ok else 'FAIL'} {err or ''}")
    if not ok:
        FAILURES.append(f"aegis hunt: {err}")

    # 5. aegis dylib-audit
    print("\n5. aegis dylib-audit...")
    ok, err = test_aegis_dylib_audit()
    print(f"   aegis dylib-audit: {'PASS' if ok else 'FAIL'} {err or ''}")
    if not ok:
        FAILURES.append(f"aegis dylib-audit: {err}")

    # 6. aegis cfg (conditional)
    print("\n6. aegis cfg...")
    ok, err = test_aegis_cfg()
    if ok is None:
        print(f"   aegis cfg: SKIP ({err})")
    elif ok:
        print("   aegis cfg: PASS")
    else:
        print(f"   aegis cfg: FAIL {err}")
        FAILURES.append(f"aegis cfg: {err}")

    # 7. tool_latent_codec bench
    print("\n7. tool_latent_codec bench-compression...")
    ok, err = test_tool_latent_bench()
    print(f"   bench-compression: {'PASS' if ok else 'FAIL'} {err or ''}")
    if not ok:
        FAILURES.append(f"bench-compression: {err}")

    # 8. council pipeline full
    print("\n8. council pipeline full...")
    ok, err = test_council_pipeline_full()
    print(f"   council pipeline full: {'PASS' if ok else 'FAIL'} {err or ''}")
    if not ok:
        FAILURES.append(f"council pipeline full: {err}")

    # Summary
    print("\n" + "=" * 50)
    if FAILURES:
        print(f"SELF-TEST FAILED — {len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"   - {f}")
        return 1
    else:
        print("SELF-TEST PASSED — all checks OK")
        return 0


if __name__ == "__main__":
    sys.exit(main())
