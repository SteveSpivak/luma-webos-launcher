#!/usr/bin/env python3
"""Negative test suite for tools/validate_docs.py.

Creates temporary repository-like structures with known issues and verifies
the validator catches them. Uses only stdlib. Safe to run in a sandbox.

All paths are resolved relative to this file (no hardcoded usernames or
host-specific directories). Uses tempfile.TemporaryDirectory() so no
destructive shutil.rmtree() is ever called on an unrelated directory.
"""

import os
import sys
import tempfile
import subprocess

# Resolve repository root from this file's location:
#   tools/test_validate_docs.py -> <repo_root>/tools/test_validate_docs.py
THIS_FILE = os.path.abspath(__file__)
TOOLS_DIR = os.path.dirname(THIS_FILE)
REPO_ROOT = os.path.dirname(TOOLS_DIR)
VALIDATOR = os.path.join(TOOLS_DIR, "validate_docs.py")

passed = 0
failed = 0


def run_validator(docs_root, repo_root=None):
    """Run the validator against a docs root and return (exit_code, output)."""
    cmd = [sys.executable, VALIDATOR, docs_root]
    if repo_root is not None:
        cmd.append(repo_root)
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=REPO_ROOT
    )
    return result.returncode, result.stdout + result.stderr


def check(condition, msg):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {msg}")
    else:
        failed += 1
        print(f"  FAIL: {msg}")


def make_repo_tree(docs_files, src_files=None):
    """Create a temp repo: tmp/docs/ + tmp/src/.

    docs_files: dict of {rel_path: content} under docs/
    src_files:  dict of {rel_path: content} under src/

    Returns (repo_path, docs_path).
    """
    tmp = tempfile.TemporaryDirectory()
    repo = os.path.join(tmp.name, "repo")
    docs = os.path.join(repo, "docs")
    src = os.path.join(repo, "src")
    os.makedirs(docs, exist_ok=True)
    os.makedirs(src, exist_ok=True)

    for rel, content in docs_files.items():
        full = os.path.join(docs, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)

    if src_files:
        for rel, content in src_files.items():
            full = os.path.join(src, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(content)

    return tmp, repo, docs


def test_broken_markdown_link():
    """A link to a nonexistent file should be flagged."""
    tmp, repo, docs = make_repo_tree(
        {"index.md": "# Index\nSee [missing](./missing.md) for details.\n"},
        {"main.rs": "fn main() {}\n"},
    )
    try:
        code, output = run_validator(docs, repo)
        check(
            code != 0 and "BROKEN LINK" in output and "missing.md" in output,
            "broken markdown link detected",
        )
    finally:
        tmp.cleanup()


def test_broken_source_ref():
    """A reference to a nonexistent source file should be flagged."""
    tmp, repo, docs = make_repo_tree(
        {"index.md": "# Guide\nSee `src/nonexistent.rs` for details.\n"},
        {"main.rs": "fn main() {}\n"},
    )
    try:
        code, output = run_validator(docs, repo)
        check(
            code != 0 and "BROKEN SOURCE REF" in output
            and "nonexistent.rs" in output,
            "broken source ref detected",
        )
    finally:
        tmp.cleanup()


def test_source_ref_with_function_suffix():
    """`src/file.rs::func()` should check the file part only."""
    tmp, repo, docs = make_repo_tree(
        {"index.md": "# Guide\nSee `src/platform.rs::normalize_apps()` for details.\n"},
        {"platform.rs": "pub fn normalize_apps() {}\n"},
    )
    try:
        code, output = run_validator(docs, repo)
        check(
            code == 0,
            "source ref with ::func() suffix handled correctly",
        )
    finally:
        tmp.cleanup()


def test_template_pattern_skipped():
    """`assets/surfaces/{brand}.png` should be skipped (template)."""
    tmp, repo, docs = make_repo_tree(
        {"index.md": "# Guide\nUse `assets/surfaces/{brand}.png` for branding.\n"},
        {},
    )
    try:
        code, output = run_validator(docs, repo)
        check(code == 0, "template pattern with {brand} skipped")
    finally:
        tmp.cleanup()


def test_planned_file_explicit_marker_skipped():
    """A source ref on a line with the planned marker should be skipped."""
    tmp, repo, docs = make_repo_tree(
        {
            "index.md": (
                "# Plan\n"
                "Create `src/new_feature.rs` "
                "<!-- docs-validate:planned --> for future work.\n"
            )
        },
        {},
    )
    try:
        code, output = run_validator(docs, repo)
        check(code == 0, "planned file with explicit marker skipped")
    finally:
        tmp.cleanup()


def test_planned_file_without_marker_is_flagged():
    """A source ref marked only with '(planned)' but no explicit marker
    should still be flagged (exemptions are narrow and auditable)."""
    tmp, repo, docs = make_repo_tree(
        {
            "index.md": (
                "# Plan\nCreate `src/new_feature.rs` (planned) for future work.\n"
            )
        },
        {},
    )
    try:
        code, output = run_validator(docs, repo)
        check(
            code != 0 and "BROKEN SOURCE REF" in output,
            "planned file without explicit marker is flagged",
        )
    finally:
        tmp.cleanup()


def test_destructive_git_reset():
    """`git reset --hard` should be flagged as destructive."""
    tmp, repo, docs = make_repo_tree(
        {"rollback.md": "# Rollback\nUse `git reset --hard 40994fc` to restore.\n"},
        {},
    )
    try:
        code, output = run_validator(docs, repo)
        check(
            code != 0 and "DESTRUCTIVE GIT RESET" in output,
            "destructive git reset detected",
        )
    finally:
        tmp.cleanup()


def test_nonexistent_workflow():
    """Reference to a nonexistent CI workflow should be flagged."""
    tmp, repo, docs = make_repo_tree(
        {"ci.md": "# CI\nSee `.github/workflows/release-pr.yml` for details.\n"},
        {},
    )
    try:
        code, output = run_validator(docs, repo)
        check(
            code != 0 and "NONEXISTENT WORKFLOW REF" in output,
            "nonexistent workflow ref detected",
        )
    finally:
        tmp.cleanup()


def test_valid_docs_pass():
    """A valid doc with real links and refs should pass."""
    tmp, repo, docs = make_repo_tree(
        {
            "real.md": "# Real page\n",
            "index.md": (
                "# Index\nSee [real](./real.md) and `src/main.rs` for details.\n"
            ),
        },
        {"main.rs": "fn main() {}\n"},
    )
    try:
        code, output = run_validator(docs, repo)
        check(code == 0, "valid docs pass without errors")
    finally:
        tmp.cleanup()


def test_broken_screenshot_ref():
    """A screenshot link to a nonexistent file should be flagged."""
    tmp, repo, docs = make_repo_tree(
        {"index.md": "# Guide\nSee `docs/screenshots/nonexistent.jpg`.\n"},
        {},
    )
    try:
        code, output = run_validator(docs, repo)
        check(
            code != 0 and "BROKEN SCREENSHOT REF" in output,
            "broken screenshot ref detected",
        )
    finally:
        tmp.cleanup()


def test_missing_index_warning():
    """A doc subdirectory without README.md should produce a warning."""
    tmp, repo, docs = make_repo_tree(
        {
            "subdir/page.md": "# Page\n",
            "index.md": "# Index\n",
        },
        {},
    )
    try:
        code, output = run_validator(docs, repo)
        check("NO INDEX" in output, "missing subdirectory index warned")
    finally:
        tmp.cleanup()


def test_broken_anchor_link():
    """A Markdown link with a broken anchor target should still resolve
    the file part (anchors are stripped before checking)."""
    tmp, repo, docs = make_repo_tree(
        {
            "real.md": "# Real page\n## Section\n",
            "index.md": "# Index\nSee [real](./real.md#section) for details.\n",
        },
        {},
    )
    try:
        code, output = run_validator(docs, repo)
        check(code == 0, "anchor link resolves file part correctly")
    finally:
        tmp.cleanup()


def test_malformed_source_ref_skipped():
    """A source-like ref containing spaces or shell syntax should be skipped."""
    tmp, repo, docs = make_repo_tree(
        {
            "index.md": (
                "# Guide\nSee `src/main.rs --release` for details.\n"
            )
        },
        {"main.rs": "fn main() {}\n"},
    )
    try:
        code, output = run_validator(docs, repo)
        check(code == 0, "malformed source ref with spaces skipped")
    finally:
        tmp.cleanup()


def test_stale_generated_inventory_flagged():
    """A generated inventory that references a nonexistent doc should be
    flagged when validated as a doc file."""
    tmp, repo, docs = make_repo_tree(
        {
            "inventory.md": (
                "# Inventory\nSee [missing](./nonexistent.md) and `src/ghost.rs`.\n"
            )
        },
        {},
    )
    try:
        code, output = run_validator(docs, repo)
        check(
            code != 0 and ("BROKEN LINK" in output or "BROKEN SOURCE REF" in output),
            "stale inventory references flagged",
        )
    finally:
        tmp.cleanup()


def test_arbitrary_checkout_directory():
    """The validator should work on an arbitrary checkout directory,
    not just the Luma repo root."""
    tmp, repo, docs = make_repo_tree(
        {
            "index.md": "# Index\nSee `src/main.rs`.\n",
        },
        {"main.rs": "fn main() {}\n"},
    )
    try:
        code, output = run_validator(docs, repo)
        check(code == 0, "arbitrary checkout directory validates correctly")
    finally:
        tmp.cleanup()


if __name__ == "__main__":
    print(f"Repository root: {REPO_ROOT}")
    print(f"Validator: {VALIDATOR}\n")
    print("Running negative test suite for tools/validate_docs.py\n")
    test_broken_markdown_link()
    test_broken_source_ref()
    test_source_ref_with_function_suffix()
    test_template_pattern_skipped()
    test_planned_file_explicit_marker_skipped()
    test_planned_file_without_marker_is_flagged()
    test_destructive_git_reset()
    test_nonexistent_workflow()
    test_valid_docs_pass()
    test_broken_screenshot_ref()
    test_missing_index_warning()
    test_broken_anchor_link()
    test_malformed_source_ref_skipped()
    test_stale_generated_inventory_flagged()
    test_arbitrary_checkout_directory()

    print(f"\nResults: {passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)