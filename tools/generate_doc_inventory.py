#!/usr/bin/env python3
"""Generate machine-readable documentation inventory and ownership matrix.

Outputs:
  tools/doc-inventory.json   - one entry per .md file under docs/
  tools/doc-ownership.csv    - doc_file -> source_file mapping

Uses only stdlib. Safe to run in a sandbox with no Rust/Node toolchain.
"""

import csv
import json
import os
import re
import sys
from pathlib import Path

DOCS_ROOT = "docs"
REPO_ROOT = os.path.abspath(os.path.join(DOCS_ROOT, os.pardir))
OUT_DIR = "tools"

# Map doc subdirectory -> (doc_type, diataxis_type, audience)
DIR_CLASSIFICATION = {
    "": ("AI agent", "explanation", "AI agents, council members"),
    "architecture": ("architecture", "explanation", "Developers, architects"),
    "developer": ("developer", "reference", "Developers, contributors"),
    "platform": ("operations", "reference", "Operations, TV integrators"),
    "reference": ("API", "reference", "Developers, API consumers"),
    "user-guide": ("user", "tutorial", "End users, power users"),
}

# Per-file overrides for doc_type / diataxis / audience
FILE_CLASSIFICATION = {
    "docs/README.md": ("AI agent", "explanation", "AI agents, new contributors"),
    "docs/overview.md": ("developer", "explanation", "All audiences"),
    "docs/developer/contributing.md": ("developer", "how-to", "Contributors"),
    "docs/developer/testing.md": ("developer", "how-to", "Developers, QA"),
    "docs/developer/ci-cd.md": ("operations", "how-to", "Release engineers, DevOps"),
    "docs/developer/build.md": ("developer", "how-to", "Developers"),
    "docs/developer/toolchain.md": ("developer", "reference", "Developers"),
    "docs/developer/code-conventions.md": ("developer", "reference", "Developers"),
    "docs/platform/webos.md": ("operations", "explanation", "TV integrators"),
    "docs/platform/luna-services.md": ("API", "reference", "TV integrators"),
    "docs/platform/root-access.md": ("operations", "reference", "TV integrators"),
    "docs/platform/native-home.md": ("operations", "how-to", "TV integrators"),
    "docs/user-guide/home-screen.md": ("user", "tutorial", "End users"),
    "docs/user-guide/navigation.md": ("user", "tutorial", "End users"),
    "docs/user-guide/apps-grid.md": ("user", "tutorial", "End users"),
    "docs/user-guide/media.md": ("user", "tutorial", "End users"),
    "docs/user-guide/games.md": ("user", "tutorial", "End users"),
    "docs/user-guide/smart-home.md": ("user", "tutorial", "End users"),
    "docs/user-guide/widgets.md": ("user", "tutorial", "End users"),
    "docs/user-guide/settings.md": ("user", "tutorial", "End users"),
    "docs/user-guide/root-features.md": ("user", "tutorial", "Power users"),
    "docs/user-guide/screens.md": ("user", "reference", "End users"),
    "docs/reference/preferences.md": ("API", "reference", "Developers"),
    "docs/reference/app-ids.md": ("API", "reference", "Developers"),
    "docs/reference/glossary.md": ("reference", "reference", "All audiences"),
}

# Nivío-scoped docs (feature-specific, not whole-project)
NIVIO_DOCS = {
    "docs/CHARTER.md", "docs/ARCHITECTURE.md", "docs/INTEGRATION-AUDIT.md",
    "docs/REUSE-MATRIX.md", "docs/USER-STORIES.md", "docs/USER-FLOWS.md",
    "docs/COMPONENTS.md", "docs/MEASUREMENT.md", "docs/RISKS-ROLLBACK.md",
    "docs/NEXT-STEP.md",
}

# Source files referenced in docs (extracted from inline code `src/xxx.rs`)
SOURCE_REF_PATTERN = re.compile(
    r"`((?:src|assets|tools|tv|native/|vector-geometry|Cargo\.toml|Cargo\.lock|"
    r"package\.json|pnpm-lock\.yaml|appinfo\.json|flake\.nix|flake\.lock|"
    r"assets/messages\.json)[^`]*)`"
)


def classify(path):
    rel = os.path.relpath(path, REPO_ROOT)
    if rel in FILE_CLASSIFICATION:
        return FILE_CLASSIFICATION[rel]
    # Derive from directory
    parts = Path(rel).parts
    if len(parts) >= 2:
        dir_name = parts[1]  # docs/<dir>/...
        if dir_name in DIR_CLASSIFICATION:
            return DIR_CLASSIFICATION[dir_name]
    return ("reference", "explanation", "General audience")


def extract_source_refs(path):
    """Extract unique source file paths referenced in a doc, stripping ::suffixes."""
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    refs = set()
    for m in SOURCE_REF_PATTERN.finditer(content):
        ref = m.group(1).strip()
        if "\n" in ref or " " in ref or "{" in ref or "}" in ref:
            continue
        if "(" in ref or ")" in ref:
            continue
        file_part = re.split(r"::", ref)[0].rstrip(".,;:!")
        # Skip planned files
        line_idx = content[:m.start()].count("\n")
        lines = content.split("\n")
        line_content = lines[line_idx] if line_idx < len(lines) else ""
        if any(marker in line_content for marker in ["(new)", "(planned)", "<!-- docs-validate:planned -->"]):
            continue
        # Only track actual repo source paths
        if file_part.startswith("src/") or file_part.startswith("assets/") or file_part.startswith("tools/") or file_part.startswith("tv/") or file_part.startswith("native/"):
            refs.add(file_part)
    return sorted(refs)


def source_exists(path):
    return os.path.exists(os.path.join(REPO_ROOT, path))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    md_files = []
    for root, dirs, files in os.walk(DOCS_ROOT):
        for f in sorted(files):
            if f.endswith(".md"):
                md_files.append(os.path.join(root, f))

    inventory = []
    ownership_rows = []  # (doc_file, source_file, exists)

    for path in md_files:
        rel = os.path.relpath(path, REPO_ROOT)
        doc_type, diataxis, audience = classify(path)
        is_nivio = rel in NIVIO_DOCS
        source_refs = extract_source_refs(path)

        entry = {
            "path": rel,
            "doc_type": doc_type,
            "diataxis": diataxis,
            "audience": audience,
            "scope": "nivio" if is_nivio else "whole-project",
            "source_refs": source_refs,
            "source_refs_resolved": [r for r in source_refs if source_exists(r)],
            "source_refs_unresolved": [r for r in source_refs if not source_exists(r)],
            "has_index": os.path.exists(os.path.join(os.path.dirname(path), "README.md")),
        }
        inventory.append(entry)

        for ref in source_refs:
            ownership_rows.append((rel, ref, source_exists(ref)))

    # Sort inventory by path
    inventory.sort(key=lambda e: e["path"])
    ownership_rows.sort(key=lambda r: (r[0], r[1]))

    # Write JSON inventory
    inventory_path = os.path.join(OUT_DIR, "doc-inventory.json")
    with open(inventory_path, "w", encoding="utf-8") as fh:
        json.dump({
            "generated_by": "tools/generate_doc_inventory.py",
            "total_docs": len(inventory),
            "whole_project_docs": sum(1 for e in inventory if e["scope"] == "whole-project"),
            "nivio_scoped_docs": sum(1 for e in inventory if e["scope"] == "nivio"),
            "docs": inventory,
        }, fh, indent=2)
    print(f"Wrote {inventory_path} ({len(inventory)} docs)")

    # Write CSV ownership matrix
    ownership_path = os.path.join(OUT_DIR, "doc-ownership.csv")
    with open(ownership_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["doc_file", "source_file", "source_exists"])
        for doc_file, src, exists in ownership_rows:
            writer.writerow([doc_file, src, "yes" if exists else "no"])
    print(f"Wrote {ownership_path} ({len(ownership_rows)} mappings)")

    # Summary of unresolved refs
    unresolved = [(e["path"], r) for e in inventory for r in e["source_refs_unresolved"]]
    if unresolved:
        print(f"\nUnresolved source refs ({len(unresolved)}):")
        for doc, ref in unresolved:
            print(f"  {doc}: {ref}")
    else:
        print("\nAll source refs resolved!")


if __name__ == "__main__":
    main()