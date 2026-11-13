#!/usr/bin/env python3
"""
scripts/xray/xray_cli.py — Fast Query CLI for the Luma Forensic Knowledge Base.

Queries docs/xray/_data/repo_graph.json in <50ms. Subcommands:

  impact <file_or_symbol>   — upstream callers, downstream deps, co-change traps, tests
  review [base_ref]         — fast scan on uncommitted changes or branch diffs
  status                    — merkle provenance check: fresh vs stale docs
  hotspots [n]              — top N radioactive files
  branches                  — all-branch divergence radar

Usage:
  python3 scripts/xray/xray_cli.py impact src/platform.rs
  python3 scripts/xray/xray_cli.py review
  python3 scripts/xray/xray_cli.py status
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(".").resolve()
DATA_DIR = REPO_ROOT / "docs" / "xray" / "_data"
GRAPH_FILE = DATA_DIR / "repo_graph.json"


def load_graph() -> dict:
    if not GRAPH_FILE.exists():
        print("ERROR: docs/xray/_data/repo_graph.json not found. Run scripts/xray/scan_repo.py first.")
        sys.exit(1)
    return json.loads(GRAPH_FILE.read_text())


def cmd_impact(target: str, graph: dict) -> None:
    nodes = graph.get("nodes", {})
    traps = graph.get("git", {}).get("co_change_traps", [])
    branches = graph.get("branches", [])

    node = nodes.get(target)
    if not node:
        for path, n in nodes.items():
            if Path(path).name == target:
                node = n
                target = path
                break

    if node:
        print(f"\nIMPACT ANALYSIS: {target}")
        print(f"  Layer: {node.get('layer')} | LOC: {node.get('loc')} | Complexity: {node.get('complexity')}")
        print(f"  Hotspot score: {node.get('hotspot_score')} | Churn: {node.get('churn')}")
        print(f"  Merkle: {node.get('merkle')}")
        symbols = node.get("symbols", [])
        if symbols:
            print(f"  Key symbols: {', '.join(symbols[:10])}")
    else:
        print(f"\nNo node found for '{target}'. Showing co-change context only.")

    relevant_traps = [t for t in traps if t.get("file_a") == target or t.get("file_b") == target]
    if relevant_traps:
        print(f"\nCO-CHANGE TRAPS (files that change with {target}):")
        for t in relevant_traps:
            other = t["file_b"] if t["file_a"] == target else t["file_a"]
            print(f"  -> {other}: Jaccard={t['jaccard']}, shared commits={t['shared_commits']}")
    else:
        print(f"\nNo co-change traps for {target}")

    touched = [b for b in branches if target in b.get("changed_files", [])]
    if touched:
        print(f"\nBRANCHES touching {target}:")
        for b in touched[:10]:
            print(f"  -> {b['branch']} (ahead={b['ahead_of_head']}, behind={b['behind_head']})")
    else:
        print(f"\nNo active branches touch {target}")


def cmd_review(base_ref: str | None, graph: dict) -> None:
    if base_ref:
        changed = subprocess.run(
            ["git", "diff", "--name-status", f"{base_ref}..HEAD"],
            capture_output=True, text=True,
        ).stdout.splitlines()
    else:
        changed = subprocess.run(
            ["git", "diff", "--name-status"],
            capture_output=True, text=True,
        ).stdout.splitlines()

    if not changed:
        print("No uncommitted changes to review.")
        return

    files = [c.split("\t")[-1] for c in changed if c]
    print(f"\nREVIEW BLAST RADIUS — {len(files)} changed file(s)")
    print(f"  Base: {base_ref or 'working tree vs index'}")

    hotspots = {h["path"]: h["score"] for h in graph.get("hotspots", [])}
    traps = graph.get("git", {}).get("co_change_traps", [])

    for f in files:
        score = hotspots.get(f, 0)
        if score > 50:
            badge = "[RADIOACTIVE]"
        elif score > 20:
            badge = "[COUPLED]"
        else:
            badge = "[STABLE]"
        print(f"\n  {badge} {f} (hotspot={score})")

        for t in traps:
            if t["file_a"] == f:
                print(f"    Co-change trap: also check {t['file_b']} (Jaccard={t['jaccard']})")
            elif t["file_b"] == f:
                print(f"    Co-change trap: also check {t['file_a']} (Jaccard={t['jaccard']})")


def cmd_status(graph: dict) -> None:
    nodes = graph.get("nodes", {})
    stale = []
    fresh = []

    for path, n in nodes.items():
        try:
            raw = (REPO_ROOT / path).read_bytes()
            if b"\x00" in raw[:1024]:
                continue
            text = raw.decode("utf-8", errors="replace")
            lines = text.splitlines()
            norm = [l.strip() for l in lines if l.strip() and not l.strip().startswith(("#", "//", "/*", "*"))]
            current_merkle = hashlib_sha256(norm)
            if current_merkle != n.get("merkle"):
                stale.append(path)
            else:
                fresh.append(path)
        except OSError:
            stale.append(path)

    print(f"\nMERKLE PROVENANCE STATUS")
    print(f"  Fresh docs: {len(fresh)}")
    print(f"  Stale docs (need refresh): {len(stale)}")
    if stale:
        print("  Stale files:")
        for f in stale[:20]:
            print(f"    -> {f}")


def hashlib_sha256(lines: list) -> str:
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]


def cmd_hotspots(n: int, graph: dict) -> None:
    hotspots = graph.get("hotspots", [])[:n]
    print(f"\nTOP {n} RADIOACTIVE HOTSPOTS")
    print(f"{'Score':>8} | {'Churn':>6} | {'InDeg':>6} | {'LOC':>6} | {'Layer':>10} | Path")
    print("-" * 90)
    for h in hotspots:
        print(f"{h['score']:>8} | {h.get('churn', 0):>6} | {h.get('in_degree', 0):>6} | {h['loc']:>6} | {h['layer']:>10} | {h['path']}")


def cmd_branches(graph: dict) -> None:
    branches = graph.get("branches", [])
    print(f"\nALL-BRANCH DIVERGENCE RADAR ({len(branches)} branches)")
    print(f"{'Branch':>30} | {'SHA':>10} | {'Ahead':>6} | {'Behind':>7} | {'Author':>15} | Subject")
    print("-" * 110)
    for b in branches[:30]:
        print(f"{b['branch']:>30} | {b['sha']:>10} | {b['ahead_of_head']:>6} | {b['behind_head']:>7} | {b['author']:>15} | {b['subject'][:50]}")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: xray_cli.py <impact|review|status|hotspots|branches> [args]")
        sys.exit(1)

    cmd = sys.argv[1]
    graph = load_graph()

    if cmd == "impact" and len(sys.argv) >= 3:
        cmd_impact(sys.argv[2], graph)
    elif cmd == "review":
        base_ref = sys.argv[2] if len(sys.argv) >= 3 else None
        cmd_review(base_ref, graph)
    elif cmd == "status":
        cmd_status(graph)
    elif cmd == "hotspots":
        n = int(sys.argv[2]) if len(sys.argv) >= 3 else 15
        cmd_hotspots(n, graph)
    elif cmd == "branches":
        cmd_branches(graph)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())