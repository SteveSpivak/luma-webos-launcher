#!/usr/bin/env python3
"""luma_cli: one read-only entrypoint for fast orientation on this checkout.

Every subcommand is a thin wrapper around existing scripts/modules in this
directory (``reference_launcher``, ``compare_reference_launcher``,
``protected_paths``, ``native_preflight``) — nothing here re-implements their
logic, and nothing here installs dependencies, builds native code, touches a
TV, or writes outside ``research/`` and ``delivery/``. Everything is driven
from ``git`` (committed content), never the live working tree, so results are
reproducible from any clone at any commit.

Commands:
  map         structural snapshot of the whole tree (dirs, extensions, docs)
  docs        documentation index + broken-relative-link check
  components  Rust module inventory, classified; layers in the pinned
              reference-fork comparison if research/audit/reference-launcher-
              facts.json exists
  review      diff-stat + protected-path flags between two revisions
  math        call any pure function in reference_launcher.py by name
  gates       run the existing native-desktop preflight (no installs)
  forensics   generic git-blob diff against an already-cloned external repo
  status      one-shot dashboard: tests, manifest, receipts, blockers, diff
  test        wrapper around the research/tests unittest discovery

Examples:
  python3 research/scripts/luma_cli.py status
  python3 research/scripts/luma_cli.py map
  python3 research/scripts/luma_cli.py components
  python3 research/scripts/luma_cli.py docs
  python3 research/scripts/luma_cli.py review
  python3 research/scripts/luma_cli.py math --list
  python3 research/scripts/luma_cli.py math shadow_quad 256 154.4 34
  python3 research/scripts/luma_cli.py math pop_peak --kw decay=5 --kw freq=10
  python3 research/scripts/luma_cli.py gates
  python3 research/scripts/luma_cli.py forensics --external-repo /path/to/clone \\
      --external-rev <sha>
"""
from __future__ import annotations

import argparse
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import reference_launcher as physics  # noqa: E402  pure math/physics primitives
import compare_reference_launcher as refcmp  # noqa: E402  module_class(), tree_entries(), git()
from protected_paths import filter_protected  # noqa: E402

BASE = "e5608cd053be5376a54a806129a332952dfabcef"
DOC_DIRS = ("delivery", "research/luma-audit")
SOURCE_PREFIXES = ("src/", "tv/", "tv-helper/", "vector-geometry/", "tools/")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def git_lines(*args: str) -> list[str]:
    out = git(*args)
    return out.splitlines() if out else []


def jprint(value) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


# --------------------------------------------------------------------------- map

def cmd_map(args: argparse.Namespace) -> int:
    rev = args.rev
    paths = git_lines("ls-tree", "-r", "--name-only", rev)
    top = {}
    for path in paths:
        head = path.split("/", 1)[0] if "/" in path else "."
        bucket = top.setdefault(head, {"files": 0, "extensions": {}})
        bucket["files"] += 1
        ext = Path(path).suffix or "(none)"
        bucket["extensions"][ext] = bucket["extensions"].get(ext, 0) + 1
    docs = [p for p in paths if p.endswith(".md")]
    scripts = sorted(p for p in paths if p.startswith("research/scripts/") and p.endswith(".py"))
    jprint({
        "rev": rev,
        "total_files": len(paths),
        "top_level": {k: {"files": v["files"], "extensions": dict(sorted(v["extensions"].items()))}
                      for k, v in sorted(top.items())},
        "markdown_files": len(docs),
        "docs": sorted(docs),
        "research_scripts": scripts,
    })
    return 0


# -------------------------------------------------------------------------- docs

HEADING = re.compile(r"^(#{1,6})\s+(.*)")
LINK = re.compile(r"\]\(([^)]+)\)")


def cmd_docs(args: argparse.Namespace) -> int:
    rev = args.rev
    broken = []
    index = {}
    for directory in args.dirs:
        paths = [p for p in git_lines("ls-tree", "-r", "--name-only", rev, "--", directory) if p.endswith(".md")]
        for path in sorted(paths):
            text = git("show", f"{rev}:{path}")
            headings = [(len(m.group(1)), m.group(2)) for m in HEADING.finditer(text) if m]
            index[path] = [f"{'  ' * (level - 1)}{title}" for level, title in headings]
            base_dir = Path(path).parent
            for link in LINK.findall(text):
                target = link.split("#", 1)[0].strip()
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                resolved = (base_dir / target)
                # Resolve against the tree at `rev`, not the live working copy.
                check = git("ls-tree", "--name-only", rev, "--",
                             str(resolved).replace("\\", "/")).strip()
                if not check:
                    broken.append({"file": path, "link": link})
    jprint({"rev": rev, "directories": list(args.dirs), "files": len(index),
            "headings": index, "broken_links": broken})
    return 1 if broken else 0


# --------------------------------------------------------------------- components

def cmd_components(args: argparse.Namespace) -> int:
    rev = args.rev
    paths = [p for p in git_lines("ls-tree", "-r", "--name-only", rev) if p.endswith(".rs")]
    modules = []
    for path in sorted(paths):
        text = git("show", f"{rev}:{path}")
        modules.append({"path": path, "lines": len(text.splitlines()), "bytes": len(text.encode()),
                         "class": refcmp.module_class(path)})
    by_class: dict[str, int] = {}
    for module in modules:
        by_class[module["class"]] = by_class.get(module["class"], 0) + 1
    result = {"rev": rev, "rust_modules": len(modules), "by_class": dict(sorted(by_class.items())),
              "modules": modules}

    facts_path = ROOT / "research/audit/reference-launcher-facts.json"
    if facts_path.exists():
        facts = json.loads(facts_path.read_text())
        # Status values in the facts file are "both", "only_ours", "only_reference".
        counts = {"shared": 0, "only_ours": 0, "only_reference": 0}
        status_to_bucket = {"both": "shared", "only_ours": "only_ours", "only_reference": "only_reference"}
        for component in facts.get("components", []):
            bucket = status_to_bucket.get(component.get("status"))
            if bucket:
                counts[bucket] += 1
        result["pinned_reference_comparison"] = {
            "note": "OBSERVED from a prior read-only clone; re-run compare_reference_launcher.py "
                    "against a freshly cloned pin to refresh. Not re-derived here.",
            "reference_commit": facts.get("reference", {}).get("commit"),
            "compared_against": facts.get("ours", {}).get("compared_rev") or facts.get("ours", {}).get("base"),
            "component_counts": counts,
            "facts_file": "research/audit/reference-launcher-facts.json",
            "report": "research/luma-audit/REFERENCE-LAUNCHER-COMPARISON.md",
        }
    else:
        result["pinned_reference_comparison"] = {
            "note": "No facts file in this checkout. The external clone used to build one does not "
                    "persist across sandbox resets; re-clone the pinned commit and run "
                    "compare_reference_launcher.py to regenerate it."
        }
    jprint(result)
    return 0


# ---------------------------------------------------------------------- review

def cmd_review(args: argparse.Namespace) -> int:
    base, rev = args.base, args.rev
    stat = git("diff", "--stat", f"{base}..{rev}") if base != rev else ""
    changed = git_lines("diff", "--name-only", f"{base}..{rev}") if base != rev else []
    protected = filter_protected(changed)
    result = {
        "base": base,
        "rev": rev,
        "files_changed": len(changed),
        "protected_files_changed": protected,
        "protected_clean": not protected,
        "diffstat_tail": stat.splitlines()[-1] if stat else "(no diff)",
    }
    if args.patch_gate:
        proc = subprocess.run([sys.executable, str(SCRIPTS / "check_patch_integrity.py")],
                               cwd=ROOT, capture_output=True, text=True, timeout=60)
        result["patch_integrity_gate"] = {"exit_code": proc.returncode,
                                           "stdout_tail": proc.stdout.strip().splitlines()[-1:] or [],
                                           "stderr_tail": proc.stderr.strip().splitlines()[-3:]}
    jprint(result)
    return 0 if result["protected_clean"] else 1


# ------------------------------------------------------------------------ math

def _physics_functions() -> dict[str, callable]:
    return {name: fn for name, fn in vars(physics).items()
            if inspect.isfunction(fn) and not name.startswith("_")}


def cmd_math(args: argparse.Namespace) -> int:
    functions = _physics_functions()
    if args.list or not args.op:
        catalog = {name: {"signature": str(inspect.signature(fn)),
                           "doc": (fn.__doc__ or "").strip().splitlines()[0] if fn.__doc__ else ""}
                   for name, fn in sorted(functions.items())}
        jprint({"module": "reference_launcher.py (pure, deterministic; MODEL, not a measurement)",
                "functions": catalog})
        return 0
    if args.op not in functions:
        print(f"unknown function {args.op!r}; run with --list", file=sys.stderr)
        return 2
    fn = functions[args.op]

    def coerce(value: str):
        try:
            return int(value) if re.fullmatch(r"-?\d+", value) else float(value)
        except ValueError:
            return value

    positional = [coerce(v) for v in args.args]
    kwargs = {}
    for item in args.kw:
        key, _, value = item.partition("=")
        kwargs[key] = coerce(value)
    try:
        result = fn(*positional, **kwargs)
    except (TypeError, ValueError) as error:
        jprint({"function": args.op, "error": str(error), "signature": str(inspect.signature(fn))})
        return 2
    jprint({"function": args.op, "args": positional, "kwargs": kwargs, "result": result,
            "label": "MODEL (pure arithmetic from the arguments given; not a device measurement)"})
    return 0


# ----------------------------------------------------------------------- gates

def cmd_gates(args: argparse.Namespace) -> int:
    proc = subprocess.run([sys.executable, str(SCRIPTS / "native_preflight.py")],
                           cwd=ROOT, capture_output=True, text=True, timeout=30)
    print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    print(f"# native_preflight.py exit={proc.returncode} "
          f"(1 means BLOCKED tools/inputs are missing; this never installs anything)")
    return proc.returncode


# ------------------------------------------------------------------- forensics

def blob_diff(ours_root: Path, ours_rev: str, external_root: Path, expected_external_rev: str | None) -> dict:
    """Generic read-only git-blob diff between two already-present repos.

    Pure given the two commits: no cloning, network access, or writes. Refuses
    to compare against a moving external ref if ``expected_external_rev`` is
    given and the external HEAD does not match it.
    """
    if not (external_root / ".git").exists():
        raise ValueError(f"not a git repo: {external_root}")
    external_head = refcmp.git(external_root, "rev-parse", "HEAD").strip()
    if expected_external_rev and external_head != expected_external_rev:
        raise ValueError(f"external HEAD {external_head} != expected {expected_external_rev}; "
                          f"refusing to compare a moving ref")
    ours = refcmp.tree_entries(ours_root, ours_rev)
    theirs = refcmp.tree_entries(external_root, "HEAD")
    shared = sorted(set(ours) & set(theirs))
    identical = [p for p in shared if ours[p] == theirs[p]]
    return {
        "ours_rev": ours_rev,
        "external_head": external_head,
        "files_ours": len(ours),
        "files_external": len(theirs),
        "shared_paths": len(shared),
        "identical_blobs": len(identical),
        "changed_blobs": len(shared) - len(identical),
        "only_ours": len(ours) - len(shared),
        "only_external": len(theirs) - len(shared),
    }


def cmd_forensics(args: argparse.Namespace) -> int:
    external = args.external_repo.resolve()
    try:
        result = blob_diff(ROOT, args.rev, external, args.external_rev)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    result["external_repo"] = str(external)
    result["note"] = "Blob comparison only; nothing is copied, cloned, or installed by this command."
    jprint(result)
    return 0


# --------------------------------------------------------------------- status

def cmd_status(args: argparse.Namespace) -> int:
    head = git("rev-parse", "HEAD").strip()
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    result = {"head": head, "branch": branch, "base": BASE}

    manifest_path = ROOT / "delivery/manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        result["manifest"] = {
            "files": len(manifest.get("files", {})),
            "candidate_patch": manifest.get("candidate_patch", {}).get("default"),
            "candidate_apply_verified": manifest.get("candidate_patch", {}).get("apply_verified"),
            "native_validation_status": manifest.get("native_validation", {}).get("status"),
            "reference_comparison_commit": manifest.get("reference_comparison", {}).get("reference_commit"),
        }

    blockers_path = ROOT / "delivery/BLOCKERS.json"
    if blockers_path.exists():
        blockers = json.loads(blockers_path.read_text())
        result["blockers"] = blockers if isinstance(blockers, list) else blockers.get("blockers", blockers)

    receipts_index = ROOT / "delivery/receipts/index.json"
    if receipts_index.exists():
        idx = json.loads(receipts_index.read_text())
        rows = idx.get("receipts", [])
        result["receipts"] = {"count": len(rows),
                               "missing": [r["label"] for r in rows if r.get("status") == "MISSING_RAW_RECEIPT"]}

    protected = filter_protected(git_lines("diff", "--name-only", f"{BASE}..{head}"))
    result["protected_paths_changed_since_base"] = protected

    tests = _run_unittest_discovery("test_*.py")
    result["research_tests"] = tests

    jprint(result)
    return 0 if tests["passed"] and not protected else 1


# ----------------------------------------------------------------------- test

def _run_unittest_discovery(pattern: str, verbose: bool = False) -> dict:
    """Run the same subprocess the rest of this project uses to test itself.

    A subprocess with ``cwd=ROOT`` is required, not an in-process TestLoader:
    two existing test files import via ``from research.scripts... import``,
    which only resolves when the *process* cwd is the repo root (the implicit
    '' sys.path entry). Running in-process from an arbitrary cwd breaks that;
    this mirrors the documented working invocation exactly instead.
    """
    argv = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "research/tests",
            "-t", "research/tests", "-p", pattern]
    if verbose:
        argv.append("-v")
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=120)
    last_line = (proc.stderr.strip().splitlines() or [""])[-1]
    match = re.search(r"Ran (\d+) tests?", proc.stderr)
    return {"exit_code": proc.returncode, "passed": proc.returncode == 0,
            "ran": int(match.group(1)) if match else None, "summary": last_line,
            "stdout": proc.stdout, "stderr": proc.stderr}


def cmd_test(args: argparse.Namespace) -> int:
    result = _run_unittest_discovery(args.pattern, args.verbose)
    print(result["stderr"], end="")
    return result["exit_code"]


# ---------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("map", help="structural snapshot of the committed tree")
    p.add_argument("--rev", default="HEAD")
    p.set_defaults(func=cmd_map)

    p = sub.add_parser("docs", help="documentation index + broken relative-link check")
    p.add_argument("--rev", default="HEAD")
    p.add_argument("--dirs", nargs="+", default=list(DOC_DIRS))
    p.set_defaults(func=cmd_docs)

    p = sub.add_parser("components", help="Rust module inventory, classified")
    p.add_argument("--rev", default="HEAD")
    p.set_defaults(func=cmd_components)

    p = sub.add_parser("review", help="diff-stat + protected-path flags between two revisions")
    p.add_argument("--base", default=BASE)
    p.add_argument("--rev", default="HEAD")
    p.add_argument("--patch-gate", action="store_true", help="also run check_patch_integrity.py")
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("math", help="call a pure function from reference_launcher.py")
    p.add_argument("op", nargs="?")
    p.add_argument("args", nargs="*")
    p.add_argument("--kw", action="append", default=[], help="name=value, may repeat")
    p.add_argument("--list", action="store_true")
    p.set_defaults(func=cmd_math)

    p = sub.add_parser("gates", help="run native_preflight.py (no installs)")
    p.set_defaults(func=cmd_gates)

    p = sub.add_parser("forensics", help="generic blob diff against an already-cloned external repo")
    p.add_argument("--external-repo", type=Path, required=True)
    p.add_argument("--external-rev", help="pinned commit the clone must be at; refuses a moving ref")
    p.add_argument("--rev", default="HEAD", help="our revision to compare from")
    p.set_defaults(func=cmd_forensics)

    p = sub.add_parser("status", help="one-shot dashboard")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("test", help="run research/tests")
    p.add_argument("--pattern", default="test_*.py")
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(func=cmd_test)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
