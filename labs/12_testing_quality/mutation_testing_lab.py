#!/usr/bin/env python3
"""
Lab 12 — Mutation Testing Quality Audit (mutmut)

Solves the "trust but don't verify" blind spot: tests exist but do they actually
find bugs? Mutation score = killed_mutants / total_mutants is the only defensible
measure of test quality. Runs mutmut against target source files and reports
mutation score + surviving mutants as a falsifiable quality gate.

Gracefully degrades when no tests exist for the target (reports as not-applicable
rather than crashing).
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MUTMUT_CONFIG_TEMPLATE = """[tool.mutmut]
paths_to_mutate = {paths}
runner = "python -m pytest {test_dir} --tb=no -q"
backup = false
"""


def _has_tests_for(target_file: str) -> bool:
    """Heuristic: check if any test file references the target module."""
    target_stem = Path(target_file).stem
    for dirpath, _dirs, files in os.walk(REPO_ROOT):
        if any(skip in dirpath for skip in {".git", "node_modules", ".venv", "__pycache__", ".agent-kb", "target"}):
            continue
        for f in files:
            if f.startswith("test_") or f.endswith("_test.py"):
                tf = Path(dirpath, f)
                try:
                    content = tf.read_text(errors="ignore")
                except OSError:
                    continue
                if target_stem in content or target_file in content:
                    return True
    return False


def run_mutation_lab(target_files: list[str]) -> dict:
    """Run mutmut mutation testing against target files."""
    t0 = time.time()
    results = {
        "lab": "mutation_testing",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "target_files": target_files,
        "mutation_score": None,
        "surviving_mutants": [],
        "killed": 0,
        "timeout": 0,
        "runtime_errors": 0,
        "total_mutants": 0,
        "duration_sec": None,
        "notes": [],
    }

    # Check mutmut is available
    try:
        subprocess.run([sys.executable, "-m", "mutmut", "--help"],
                       capture_output=True, check=True, timeout=30)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        results["notes"].append("mutmut not installed — skipping mutation testing")
        results["duration_sec"] = round(time.time() - t0, 2)
        return results

    # Filter to targets that have tests (mutation testing needs tests to kill mutants)
    testable = [f for f in target_files if _has_tests_for(f)]
    untestable = [f for f in target_files if f not in testable]
    for f in untestable:
        results["notes"].append(f"No tests found for {f} — mutation testing not applicable")

    if not testable:
        results["notes"].append("No testable targets — mutation score N/A")
        results["duration_sec"] = round(time.time() - t0, 2)
        return results

    # Build a temporary pyproject.toml mutmut config so we only mutate the target files
    paths_json = json.dumps(testable)
    config_content = MUTMUT_CONFIG_TEMPLATE.format(paths=paths_json, test_dir="labs")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_pyproject = Path(tmpdir) / "pyproject.toml"
        tmp_pyproject.write_text(config_content)
        env = {**os.environ, "MUTUT_CONFIG_PATH": str(tmp_pyproject)}

        cmd = [sys.executable, "-m", "mutmut", "run", "--suspicious-policy=ignore"]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True,
                              timeout=300, env=env)

    # Parse mutmut summary text output
    text = proc.stdout + proc.stderr
    for line in text.splitlines():
        line = line.strip()
        if "killed" in line.lower() or "mutants" in line.lower() or "score" in line.lower():
            results.setdefault("_raw", []).append(line)

    # Try to extract numbers from output like "X killed, Y survived, Z timeout"
    import re
    killed_m = re.search(r"(\d+)\s+killed", text, re.I)
    survived_m = re.search(r"(\d+)\s+survived", text, re.I)
    timeout_m = re.search(r"(\d+)\s+timeout", text, re.I)
    total_m = re.search(r"(\d+)\s+mutant", text, re.I)

    if killed_m:
        results["killed"] = int(killed_m.group(1))
    if survived_m:
        results["surviving_mutants"] = [{"note": "see _raw for details"}]
    if timeout_m:
        results["timeout"] = int(timeout_m.group(1))
    if total_m:
        results["total_mutants"] = int(total_m.group(1))

    # Compute total if we have the parts
    if results["total_mutants"] == 0:
        results["total_mutants"] = results["killed"] + len(results["surviving_mutants"]) + results["timeout"] + results["runtime_errors"]

    if results["total_mutants"] > 0:
        results["mutation_score"] = round(results["killed"] / results["total_mutants"] * 100, 2)
    else:
        results["mutation_score"] = None
        results["notes"].append("Mutmut ran but reported 0 mutants — check that pytest can collect tests")

    results["exit_code"] = proc.returncode
    results["duration_sec"] = round(time.time() - t0, 2)
    return results


if __name__ == "__main__":
    targets = sys.argv[1:] or ["scripts/hyper_runner.py"]
    out = run_mutation_lab(targets)
    print(json.dumps(out, indent=2))
