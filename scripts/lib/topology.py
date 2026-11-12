"""
scripts/lib/topology.py — Spectral graph topology for repo dependency analysis.

Computes:
  - Connected components C
  - First Betti number β1 = |E_undir| - |V| + C (cycle rank / spaghetti measure)
  - Tarjan SCCs (directed circular dependency clusters)
  - PageRank centrality (load-bearing modules)
  - Fiedler λ2 algebraic connectivity (via Rayleigh-quotient power iteration)

Pure stdlib + optional numpy if available.
"""
from __future__ import annotations

import collections
import os
from pathlib import Path

IGNORE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__",
    ".agent-kb", ".mypy_cache", ".pytest_cache", "target", "vendor",
}


def iter_py_files(root: Path):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for f in sorted(files):
            if f.endswith(".py"):
                yield Path(dirpath, f)


def build_dependency_graph(root: Path):
    import ast
    dotted_map: dict[str, Path] = {}
    for p in iter_py_files(root):
        rel = p.relative_to(root)
        parts = list(rel.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            dotted_map[".".join(parts)] = p

    nodes = sorted(set(str(p.relative_to(root)) for p in dotted_map.values()))
    node_to_rel = {mod: str(p.relative_to(root)) for mod, p in dotted_map.items()}
    rel_to_node = {v: k for k, v in node_to_rel.items()}

    adj_dir = collections.defaultdict(set)
    adj_undir = collections.defaultdict(set)

    for mod, p in dotted_map.items():
        u_rel = str(p.relative_to(root))
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                targets = [node.module]
            for t in targets:
                parts = t.split(".")
                for k in range(len(parts), 0, -1):
                    cand = ".".join(parts[:k])
                    if cand in dotted_map:
                        v_rel = str(dotted_map[cand].relative_to(root))
                        if u_rel != v_rel:
                            adj_dir[u_rel].add(v_rel)
                            adj_undir[u_rel].add(v_rel)
                            adj_undir[v_rel].add(u_rel)
                        break

    return nodes, adj_dir, adj_undir


def connected_components(nodes, adj_undir):
    visited = set()
    comps = 0
    for u in nodes:
        if u in visited:
            continue
        comps += 1
        stack = [u]
        visited.add(u)
        while stack:
            cur = stack.pop()
            for nxt in adj_undir[cur]:
                if nxt not in visited:
                    visited.add(nxt)
                    stack.append(nxt)
    return comps


def tarjan_sccs(nodes, adj_dir):
    indices = {}
    lowlink = {}
    on_stack = set()
    stack = []
    sccs = []
    counter = [0]
    import sys
    sys.setrecursionlimit(max(5000, len(nodes) * 4))

    def strongconnect(u):
        indices[u] = lowlink[u] = counter[0]
        counter[0] += 1
        stack.append(u)
        on_stack.add(u)
        for v in adj_dir.get(u, ()):
            if v not in indices:
                strongconnect(v)
                lowlink[u] = min(lowlink[u], lowlink[v])
            elif v in on_stack:
                lowlink[u] = min(lowlink[u], indices[v])
        if lowlink[u] == indices[u]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == u:
                    break
            if len(comp) > 1:
                sccs.append(sorted(comp))

    for u in nodes:
        if u not in indices:
            strongconnect(u)
    return sccs


def pagerank(nodes, adj_dir, iterations=30, damping=0.85):
    N = max(1, len(nodes))
    pr = {u: 1.0 / N for u in nodes}
    for _ in range(iterations):
        nxt = {u: (1.0 - damping) / N for u in nodes}
        for u in nodes:
            outs = adj_dir.get(u, set())
            if outs:
                share = damping * pr[u] / len(outs)
                for v in outs:
                    nxt[v] += share
        pr = nxt
    return pr


def fiedler_lambda2(nodes, adj_undir, iterations=50):
    """Rayleigh-quotient power iteration on the graph Laplacian to estimate λ2."""
    import math
    N = len(nodes)
    if N < 2:
        return 0.0
    idx = {u: i for i, u in enumerate(nodes)}

    # Laplacian L = D - A
    deg = {u: len(adj_undir.get(u, set())) for u in nodes}

    def matvec(v):
        out = [0.0] * N
        for u in nodes:
            i = idx[u]
            out[i] += deg[u] * v[i]
            for nxt in adj_undir.get(u, set()):
                out[i] -= v[idx[nxt]]
        return out

    # Start with random-ish vector orthogonal to ones
    v = [1.0 if i % 2 == 0 else -1.0 for i in range(N)]
    # orthogonalize against constant vector
    mean = sum(v) / N
    v = [x - mean for x in v]
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    v = [x / norm for x in v]

    lam = 0.0
    for _ in range(iterations):
        lv = matvec(v)
        # Rayleigh quotient
        num = sum(v[i] * lv[i] for i in range(N))
        den = sum(x * x for x in v) or 1.0
        lam = num / den
        # power step
        norm = math.sqrt(sum(x * x for x in lv)) or 1.0
        v = [x / norm for x in lv]
    return max(0.0, lam)


def analyze(root: Path):
    nodes, adj_dir, adj_undir = build_dependency_graph(root)
    comps = connected_components(nodes, adj_undir)
    undir_edges = sum(len(v) for v in adj_undir.values()) // 2
    dir_edges = sum(len(v) for v in adj_dir.values())
    betti = max(0, undir_edges - len(nodes) + comps)
    sccs = tarjan_sccs(nodes, adj_dir)
    pr = pagerank(nodes, adj_dir)
    lam2 = fiedler_lambda2(nodes, adj_undir)

    top_pr = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:15]
    return {
        "vertices": len(nodes),
        "directed_edges": dir_edges,
        "undirected_edges": undir_edges,
        "connected_components": comps,
        "first_betti_number": betti,
        "tarjan_scc_count": len(sccs),
        "circular_dependency_sccs": [sorted(s) for s in sccs[:10]],
        "top_pagerank": [(k, round(v, 6)) for k, v in top_pr],
        "fiedler_lambda2": round(lam2, 6),
    }
