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
    python3 tools/validate_docs.py [docs_root] [repo_root]

If repo_root is omitted, it is resolved as the parent of docs_root.
Exits non-zero if any check fails.
"""

import os
import re
import sys
from pathlib import Path

# Explicit, auditable marker for planned (not-yet-existing) source files.
# A source reference on a line containing this marker is exempted from the
# existence check. This prevents silently ignoring real missing paths.
PLANNED_MARKER = "<!-- docs-validate:planned -->"

# Source-file path prefixes that qualify as repo source references.
SOURCE_PREFIXES = (
    "src/",
    "assets/",
    "tools/",
    "tv/",
    "native/",
    "vector-geometry",
    "Cargo.toml",
    "Cargo.lock",
    "package.json",
    "pnpm-lock.yaml",
    "appinfo.json",
    "flake.nix",
    "flake.lock",
    "assets/messages.json",
)


class ValidationContext:
    """Holds repository root, docs root, and accumulated results."""

    def __init__(self, docs_root, repo_root=None):
        self.docs_root = os.path.abspath(docs_root)
        self.repo_root = os.path.abspath(repo_root) if repo_root else \
            os.path.abspath(os.path.join(self.docs_root, os.pardir))
        self.errors = []
        self.warnings = []

    def add_error(self, msg):
        self.errors.append(msg)

    def add_warning(self, msg):
        self.warnings.append(msg)

    @property
    def failed(self):
        return len(self.errors) > 0


def check_link(ctx, path, link, context):
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
        ctx.add_error(f"BROKEN LINK in {path}: {link} -> {full_path} [{context}]")


def check_source_ref(ctx, path, ref, context):
    """Check a source file reference exists in the repo tree."""
    ref = ref.strip("./")
    full_path = os.path.join(ctx.repo_root, ref)
    if not os.path.exists(full_path):
        ctx.add_error(f"BROKEN SOURCE REF in {path}: {ref} -> {full_path} [{context}]")


def check_screenshot_ref(ctx, path, ref, context):
    """Check a screenshot reference exists."""
    full_path = os.path.join(ctx.repo_root, ref)
    if not os.path.exists(full_path):
        ctx.add_error(f"BROKEN SCREENSHOT REF in {path}: {ref} -> {full_path} [{context}]")


def check_no_destructive_reset(ctx, path, content, context):
    """Check for destructive git reset commands in rollback guidance."""
    if re.search(r"git\s+reset\s+--hard", content):
        ctx.add_error(f"DESTRUCTIVE GIT RESET in {path}: {context}")


def check_no_nonexistent_workflow(ctx, path, content, context):
    """Check for references to CI workflows that don't exist."""
    workflows_dir = os.path.join(ctx.repo_root, ".github", "workflows")
    actual_workflows = set()
    if os.path.isdir(workflows_dir):
        actual_workflows = {
            f for f in os.listdir(workflows_dir)
            if f.endswith(".yml") or f.endswith(".yaml")
        }

    for m in re.finditer(
        r"\.github/workflows/([^\s`]+\.(?:yml|yaml))", content
    ):
        wf = m.group(1)
        if wf not in actual_workflows:
            ctx.add_error(
                f"NONEXISTENT WORKFLOW REF in {path}: .github/workflows/{wf} [{context}]"
            )


def check_index_exists(ctx, path):
    """Check that each doc folder has a README.md index."""
    dir_path = os.path.dirname(path)
    readme = os.path.join(dir_path, "README.md")
    if not os.path.exists(readme):
        docs_readme = os.path.join(ctx.repo_root, ctx.docs_root, "README.md")
        if os.path.abspath(dir_path) != os.path.abspath(docs_readme):
            ctx.add_warning(
                f"NO INDEX: {dir_path} lacks README.md "
                f"(docs/README.md exists at repo level)"
            )


def is_planned_ref(line_content):
    """Return True if the line marks the reference as planned (exempt)."""
    return PLANNED_MARKER in line_content


def is_malformed_source_ref(ref):
    """Return True if the reference should not be checked as a file path."""
    if "\n" in ref or " " in ref:
        return True
    if ref.startswith("$") or ref.startswith("#"):
        return True
    if "{" in ref or "}" in ref:
        return True
    if "(" in ref or ")" in ref:
        return True
    return False


def source_file_part(ref):
    """Strip ::function() / ::Type suffixes and trailing punctuation."""
    file_part = re.split(r"::", ref)[0]
    return file_part.rstrip(".,;:!")


def is_repo_source_path(file_part):
    """Return True if the path looks like a repo source reference."""
    return any(
        file_part.startswith(prefix) or file_part == prefix
        for prefix in SOURCE_PREFIXES
    )


def validate_file(ctx, path):
    """Run all checks on a single markdown file."""
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    lines = content.split("\n")

    # Markdown links [text](url)
    for m in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", content):
        text, url = m.group(1), m.group(2)
        check_link(ctx, path, url, f"[{text}]({url})")

    # Source file references in inline code: `src/foo.rs`
    for m in re.finditer(
        r"`((?:src|assets|tools|tv|native/|vector-geometry|Cargo\.toml|"
        r"Cargo\.lock|package\.json|pnpm-lock\.yaml|appinfo\.json|"
        r"flake\.nix|flake\.lock|assets/messages\.json)[^`]*)`",
        content,
    ):
        ref = m.group(1).strip()
        if is_malformed_source_ref(ref):
            continue
        line_idx = content[: m.start()].count("\n")
        line_content = lines[line_idx] if line_idx < len(lines) else ""
        if is_planned_ref(line_content):
            continue
        file_part = source_file_part(ref)
        if not is_repo_source_path(file_part):
            continue
        check_source_ref(ctx, path, file_part, f"`{ref}`")

    # Screenshot references
    for m in re.finditer(
        r"(?:docs/)?screenshots/([^\s`)]+\.(?:jpg|png|webp|gif))", content
    ):
        ref = "docs/screenshots/" + m.group(1)
        check_screenshot_ref(ctx, path, ref, f"screenshots/{m.group(1)}")

    # Destructive git reset
    check_no_destructive_reset(ctx, path, content, "rollback guidance")

    # Nonexistent workflow references
    check_no_nonexistent_workflow(ctx, path, content, "CI workflow reference")

    # Index README
    check_index_exists(ctx, path)


def validate_docs(docs_root, repo_root=None):
    """Validate all markdown files under docs_root.

    Returns a ValidationContext with accumulated errors and warnings.
    """
    ctx = ValidationContext(docs_root, repo_root)
    md_files = []
    for root, dirs, files in os.walk(docs_root):
        for f in sorted(files):
            if f.endswith(".md"):
                md_files.append(os.path.join(root, f))

    for path in md_files:
        validate_file(ctx, path)

    return ctx


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    docs_root = argv[0] if len(argv) > 0 else "docs"
    repo_root = argv[1] if len(argv) > 1 else None

    ctx = validate_docs(docs_root, repo_root)

    print(f"Documentation files checked: "
          f"{sum(1 for _ in __import__('os').walk(docs_root) for f in _[2] if f.endswith('.md'))}")
    print(f"Errors: {len(ctx.errors)}")
    print(f"Warnings: {len(ctx.warnings)}")

    if ctx.warnings:
        print("\n--- Warnings ---")
        for w in ctx.warnings:
            print(f"  {w}")

    if ctx.errors:
        print("\n--- ERRORS ---")
        for e in ctx.errors:
            print(f"  {e}")
        return 1

    print("\nAll documentation checks passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())