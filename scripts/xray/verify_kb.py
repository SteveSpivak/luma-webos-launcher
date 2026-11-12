#!/usr/bin/env python3
"""
scripts/xray/verify_kb.py — Automated Knowledge Base & Clarity Verifier (M1-M6 Gate).

Audits citation accuracy, BLUF/ADHD structural compliance, Mermaid safety,
and Hotspot coverage against docs/xray/ and docs/xray/_data/repo_graph.json.

Exit codes:
  0 — all gates pass
  1 — one or more gates fail
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(".").resolve()
XRAY_DIR = REPO_ROOT / "docs" / "xray"
GRAPH_FILE = XRAY_DIR / "_data" / "repo_graph.json"

CITATION_RE = re.compile(r"\[([^\]]+)\]\(([^)#:\s]+)(?:#L?(\d+)(?:-L?(\d+))?)?\)")
MERMAID_BLOCK_RE = re.compile(r"```mermaid\s+(.*?)```", re.S)
PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|INSERT_HERE|PLACEHOLDER)\b")


def sha256_lines(lines):
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]


def audit_kb():
    if not XRAY_DIR.exists():
        print("FAIL: docs/xray/ directory does not exist.")
        sys.exit(1)

    md_files = sorted(XRAY_DIR.rglob("*.md"))
    if not md_files:
        print("FAIL: No Markdown files found in docs/xray/.")
        sys.exit(1)

    total_citations = 0
    valid_citations = 0
    bluf_compliant = 0
    mermaid_blocks = 0
    valid_mermaid = 0
    long_paragraphs = 0
    placeholders_found = 0
    all_kb_text = []

    for md in md_files:
        text = md.read_text(encoding="utf-8", errors="replace")
        all_kb_text.append(text)
        lines = text.splitlines()

        top_chunk = "\n".join(lines[:12]).upper()
        if "BLUF" in top_chunk:
            bluf_compliant += 1

        in_code = False
        consec_prose = 0
        for l in lines:
            s = l.strip()
            if s.startswith("```"):
                in_code = not in_code
                consec_prose = 0
                continue
            if in_code or not s or s.startswith(("#", ">", "|", "-", "*", "<", "1.", "2.", "3.")):
                consec_prose = 0
            else:
                consec_prose += 1
                if consec_prose > 5:
                    long_paragraphs += 1
                    consec_prose = 0

        placeholders_found += len(PLACEHOLDER_RE.findall(text))

        for _, rel_target, l_start, _ in CITATION_RE.findall(text):
            if rel_target.startswith(("http://", "https://", "#")):
                continue
            total_citations += 1
            candidate = (md.parent / rel_target).resolve()
            if not candidate.exists():
                candidate = (REPO_ROOT / rel_target).resolve()
            if candidate.exists() and candidate.is_file():
                if l_start:
                    try:
                        file_line_count = len(candidate.read_text(errors="replace").splitlines())
                        if 1 <= int(l_start.lstrip("L")) <= max(1, file_line_count + 5):
                            valid_citations += 1
                    except OSError:
                        pass
                else:
                    valid_citations += 1

        for block in MERMAID_BLOCK_RE.findall(text):
            mermaid_blocks += 1
            first_line = block.strip().splitlines()[0] if block.strip() else ""
            valid_hdr = any(first_line.startswith(h) for h in (
                "flowchart", "graph", "sequenceDiagram", "stateDiagram",
                "erDiagram", "gitGraph", "C4",
            ))
            node_defs = len(re.findall(r"-->|---|-\.->|==>|-\>>", block))
            if valid_hdr and 1 <= node_defs <= 45:
                valid_mermaid += 1

    full_corpus = "\n".join(all_kb_text)

    hotspot_recall = 1.0
    if GRAPH_FILE.exists():
        g = json.loads(GRAPH_FILE.read_text())
        nodes = list(g.get("nodes", {}).values()) if isinstance(g.get("nodes"), dict) else g.get("nodes", [])
        nodes.sort(key=lambda x: x.get("hotspot_score", 0), reverse=True)
        top_hotspots = [n["path"] for n in nodes[:15] if "path" in n]
        if top_hotspots:
            covered = sum(1 for hp in top_hotspots if hp in full_corpus or Path(hp).name in full_corpus)
            hotspot_recall = covered / len(top_hotspots)

    cir = (valid_citations / total_citations * 100) if total_citations else 0.0
    bluf_rate = (bluf_compliant / len(md_files) * 100)
    mermaid_rate = (valid_mermaid / mermaid_blocks * 100) if mermaid_blocks else 0.0

    scorecard = {
        "files_audited": len(md_files),
        "M1_citation_integrity_pct": round(cir, 1),
        "M2_top15_hotspot_recall_pct": round(hotspot_recall * 100, 1),
        "M4_bluf_header_compliance_pct": round(bluf_rate, 1),
        "mermaid_diagrams_valid": f"{valid_mermaid}/{mermaid_blocks} ({round(mermaid_rate, 1)}%)",
        "adhd_wall_of_text_violations": long_paragraphs,
        "unfinished_placeholders": placeholders_found,
    }
    print(json.dumps(scorecard, indent=2))

    passed = (
        cir >= 95.0
        and hotspot_recall >= 0.90
        and bluf_rate == 100.0
        and mermaid_blocks >= 3
        and mermaid_rate == 100.0
        and placeholders_found == 0
    )
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    audit_kb()