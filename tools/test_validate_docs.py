#!/usr/bin/env python3
"""Negative test suite for tools/validate_docs.py.

Creates temporary markdown files with known issues and verifies the
validator catches them. Uses only stdlib. Safe to run in a sandbox.
"""

import os
import sys
import tempfile
import shutil
import subprocess

REPO_ROOT = "/home/user/luma-webos-launcher"
VALIDATOR = os.path.join(REPO_ROOT, "tools", "validate_docs.py")

passed = 0
failed = 0


def run_validator(docs_root):
    result = subprocess.run(
        [sys.executable, VALIDATOR, docs_root],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    return result.returncode, result.stdout + result.stderr


def make_test_dir(name):
    """Create a temp repo-like structure: tmp_repo/docs/ + tmp_repo/src/.
    Returns the docs root path (what we pass to the validator).
    """
    repo = os.path.join(tempfile.gettempdir(), f"docval_test_{name}")
    if os.path.exists(repo):
        shutil.rmtree(repo)
    os.makedirs(os.path.join(repo, "docs"), exist_ok=True)
    os.makedirs(os.path.join(repo, "src"), exist_ok=True)
    return os.path.join(repo, "docs")


def check(condition, msg):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {msg}")
    else:
        failed += 1
        print(f"  FAIL: {msg}")


def test_broken_markdown_link():
    d = make_test_dir("broken_link")
    with open(os.path.join(d, "index.md"), "w") as f:
        f.write("# Index\nSee [missing](./missing.md) for details.\n")
    code, output = run_validator(d)
    check(code != 0 and "BROKEN LINK" in output and "missing.md" in output,
          "broken markdown link detected")


def test_broken_source_ref():
    d = make_test_dir("broken_source")
    with open(os.path.join(d, "index.md"), "w") as f:
        f.write("# Guide\nSee `src/nonexistent.rs` for details.\n")
    code, output = run_validator(d)
    check(code != 0 and "BROKEN SOURCE REF" in output and "nonexistent.rs" in output,
          "broken source ref detected")


def test_source_ref_with_function_suffix():
    d = make_test_dir("func_suffix")
    with open(os.path.join(d, "index.md"), "w") as f:
        f.write("# Guide\nSee `src/platform.rs::normalize_apps()` for details.\n")
    code, output = run_validator(d)
    check(code == 0,
          "source ref with ::func() suffix handled correctly")


def test_template_pattern_skipped():
    d = make_test_dir("template")
    with open(os.path.join(d, "index.md"), "w") as f:
        f.write("# Guide\nUse `assets/surfaces/{brand}.png` for branding.\n")
    code, output = run_validator(d)
    check(code == 0,
          "template pattern with {brand} skipped")


def test_planned_file_skipped():
    d = make_test_dir("planned")
    with open(os.path.join(d, "index.md"), "w") as f:
        f.write("# Plan\nCreate `src/new_feature.rs` (planned) for future work.\n")
    code, output = run_validator(d)
    check(code == 0,
          "planned file reference skipped")


def test_destructive_git_reset():
    d = make_test_dir("destructive")
    with open(os.path.join(d, "rollback.md"), "w") as f:
        f.write("# Rollback\nUse `git reset --hard 40994fc` to restore.\n")
    code, output = run_validator(d)
    check(code != 0 and "DESTRUCTIVE GIT RESET" in output,
          "destructive git reset detected")


def test_nonexistent_workflow():
    d = make_test_dir("workflow")
    with open(os.path.join(d, "ci.md"), "w") as f:
        f.write("# CI\nSee `.github/workflows/release-pr.yml` for details.\n")
    code, output = run_validator(d)
    check(code != 0 and "NONEXISTENT WORKFLOW REF" in output,
          "nonexistent workflow ref detected")


def test_valid_docs_pass():
    d = make_test_dir("valid")
    repo = os.path.dirname(d)  # parent of docs/ is the repo root
    # Create a real source file in the repo root so source refs resolve
    with open(os.path.join(repo, "src", "main.rs"), "w") as f:
        f.write("fn main() {}\n")
    with open(os.path.join(d, "real.md"), "w") as f:
        f.write("# Real page\n")
    with open(os.path.join(d, "index.md"), "w") as f:
        f.write("# Index\nSee [real](./real.md) and `src/main.rs` for details.\n")
    code, output = run_validator(d)
    check(code == 0,
          "valid docs pass without errors")


def test_broken_screenshot_ref():
    d = make_test_dir("screenshot")
    with open(os.path.join(d, "index.md"), "w") as f:
        f.write("# Guide\nSee `docs/screenshots/nonexistent.jpg`.\n")
    code, output = run_validator(d)
    check(code != 0 and "BROKEN SCREENSHOT REF" in output,
          "broken screenshot ref detected")


if __name__ == "__main__":
    print("Running negative test suite for tools/validate_docs.py\n")
    test_broken_markdown_link()
    test_broken_source_ref()
    test_source_ref_with_function_suffix()
    test_template_pattern_skipped()
    test_planned_file_skipped()
    test_destructive_git_reset()
    test_nonexistent_workflow()
    test_valid_docs_pass()
    test_broken_screenshot_ref()

    print(f"\nResults: {passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)