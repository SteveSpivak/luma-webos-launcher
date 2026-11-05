#!/usr/bin/env python3
"""Stdlib-only documentation validator for Luma.

Checks:
1. All relative Markdown links resolve to existing files.
2. All source-file references (e.g. `src/platform.rs`) point to existing files.
3. All screenshot references (e.g. `docs/screenshots/X.jpg`) point to existing files.
4. No destructive git reset commands in rollback guidance.
5. No references to non-existent CI workflow files.
6. All documentation files have a parent index (README.md in same or parent dir).

Usage:
    python3 tools/validate_docs.py [docs_root]

Exits non-zero if any check fails.
"""

import os
import re
import sys
from pathlib import Path

DOCS_ROOT = sys.argv[1] if len(sys.argv) > 1 else "docs"
REPO_ROOT = os.path.abspath(os.path.join(DOCS_ROOT, os.pardir))

errors = []
warnings = []


def add_error(msg):
    errors.append(msg)


def add_warning(msg):
    warnings.append(msg)


def check_link(path, link, context):
    """Check a relative Markdown link resolves."""
    if link.startswith(("http://", "https://", "mailto:")):
        return
    if link.startswith("#"):
        return
    if "#" in link:
        link = link.split("#")[0]
    if not link:
        return
    base_dir = os.path.dirname(path)
    full_path = os.path.normpath(os.path.join(base_dir, link))
    if not os.path.exists(full_path):
        add_error(f"BROKEN LINK in {path}: {link} -> {full_path} [{context}]")


def check_source_ref(path, ref, context):
    """Check a source file reference exists in the repo tree."""
    # Normalize: strip leading ./ or /
    ref = ref.strip("./")
    full_path = os.path.join(REPO_ROOT, ref)
    if not os.path.exists(full_path):
        add_error(f"BROKEN SOURCE REF in {path}: {ref} -> {full_path} [{context}]")


def check_screenshot_ref(path, ref, context):
    """Check a screenshot reference exists."""
    full_path = os.path.join(REPO_ROOT, ref)
    if not os.path.exists(full_path):
        add_error(f"BROKEN SCREENSHOT REF in {path}: {ref} -> {full_path} [{context}]")


def check_no_destructive_reset(path, content, context):
    """Check for destructive git reset commands in rollback guidance."""
    if re.search(r"git\s+reset\s+--hard", content):
        add_error(f"DESTRUCTIVE GIT RESET in {path}: {context}")


def check_no_nonexistent_workflow(path, content, context):
    """Check for references to CI workflows that don't exist."""
    workflows_dir = os.path.join(REPO_ROOT, ".github", "workflows")
    actual_workflows = set()
    if os.path.isdir(workflows_dir):
        actual_workflows = {f for f in os.listdir(workflows_dir) if f.endswith(".yml") or f.endswith(".yaml")}

    for m in re.finditer(r"\.github/workflows/([^\s`]+\.(?:yml|yaml))", content):
        wf = m.group(1)
        if wf not in actual_workflows:
            add_error(f"NONEXISTENT WORKFLOW REF in {path}: .github/workflows/{wf} [{context}]")


def check_index_exists(path):
    """Check that each doc folder has a README.md index."""
    dir_path = os.path.dirname(path)
    readme = os.path.join(dir_path, "README.md")
    if not os.path.exists(readme):
        # Allow root-level docs files without a sibling README if docs/README.md exists
        docs_readme = os.path.join(REPO_ROOT, DOCS_ROOT, "README.md")
        if os.path.abspath(dir_path) != os.path.abspath(os.path.join(REPO_ROOT, DOCS_ROOT)):
            add_warning(f"NO INDEX: {dir_path} lacks README.md (docs/README.md exists at repo level)")


# Walk all markdown files
md_files = []
for root, dirs, files in os.walk(DOCS_ROOT):
    for f in sorted(files):
        if f.endswith(".md"):
            md_files.append(os.path.join(root, f))

for path in md_files:
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Check Markdown links [text](url)
    for m in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", content):
        text, url = m.group(1), m.group(2)
        check_link(path, url, f"[{text}]({url})")

    # Check source file references in inline code: `src/foo.rs`
    # Only match single-path references, not code blocks
    lines = content.split("\n")
    for m in re.finditer(r"`((?:src|assets|tools|tv|native/|vector-geometry|Cargo\.toml|Cargo\.lock|package\.json|pnpm-lock\.yaml|appinfo\.json|flake\.nix|flake\.lock|assets/messages\.json)[^`]*)`", content):
        ref = m.group(1).strip()
        # Skip if it looks like a code snippet (contains spaces, newlines, shell syntax)
        if "\n" in ref or " " in ref or ref.startswith("$") or ref.startswith("#"):
            continue
        # Skip template patterns with placeholders like {brand}
        if "{" in ref or "}" in ref:
            continue
        # Skip code-like patterns with parens or dots in non-extension positions
        if "(" in ref or ")" in ref:
            continue
        # Skip planned/new files (referenced as future work, e.g. on a feature branch)
        line_idx = content[:m.start()].count("\n")
        line_content = lines[line_idx] if line_idx < len(lines) else ""
        if any(marker in line_content for marker in ["(new)", "(planned)", "<!-- docs-validate:planned -->", "TODO:", "FIXME:"]):
            continue
        # Strip ::function() or ::Type suffixes before checking file existence
        file_part = re.split(r"::", ref)[0]
        # Also strip trailing punctuation that isn't part of a path
        file_part = file_part.rstrip(".,;:!")
        check_source_ref(path, file_part, f"`{ref}`")

    # Check screenshot references
    for m in re.finditer(r"(?:docs/)?screenshots/([^\s`)]+\.(?:jpg|png|webp|gif))", content):
        ref = "docs/screenshots/" + m.group(1)
        check_screenshot_ref(path, ref, f"screenshots/{m.group(1)}")

    # Check for destructive git reset
    check_no_destructive_reset(path, content, "rollback guidance")

    # Check for nonexistent workflow references
    check_no_nonexistent_workflow(path, content, "CI workflow reference")

    # Check for index README
    check_index_exists(path)


# Summary
print(f"Documentation files checked: {len(md_files)}")
print(f"Errors: {len(errors)}")
print(f"Warnings: {len(warnings)}")

if warnings:
    print("\n--- Warnings ---")
    for w in warnings:
        print(f"  {w}")

if errors:
    print("\n--- ERRORS ---")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)

print("\nAll documentation checks passed!")
sys.exit(0)