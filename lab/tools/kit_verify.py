#!/usr/bin/env python3
"""Offline integrity verifier for the pinned old-Luma file transfers.
No network, mutation, credentials or device access. Prints JSON on stdout.
Exit 1 if any file missing/mismatch, including negative-test fixtures.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "lab/reference-import-manifest.json"

def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def audit(root: Path = ROOT, manifest: Path = MANIFEST) -> dict:
    config = json.loads(manifest.read_text(encoding="utf-8"))
    if config.get("schema") != "luma-nuvio-reference-import/1":
        raise ValueError("unknown import schema")
    rows, seen = [], set()
    for record in config["files"]:
        rel = record["target_path"]
        if not isinstance(rel, str) or rel.startswith("/") or "\\" in rel or ".." in Path(rel).parts or rel in seen:
            raise ValueError("unsafe or duplicate target path")
        seen.add(rel)
        expected = record["source_blob_sha"]
        path = root / rel
        if not path.is_file() or path.is_symlink():
            rows.append({"path":rel,"status":"MISSING_OR_SYMLINK"})
            continue
        actual = git_blob_sha(path.read_bytes())
        rows.append({"path":rel,"status":"PASS" if actual == expected else "MISMATCH",
                     "git_blob_sha":actual})
    return {"schema":"luma-reference-integrity/1","source_commit":config["source_commit"],
            "counts":{"files":len(rows),"passed":sum(x["status"]=="PASS" for x in rows)},
            "status":"PASS" if rows and all(x["status"]=="PASS" for x in rows) else "FAIL",
            "files":rows}

def main() -> int:
    try:
        result=audit()
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        result={"status":"FAIL","error":type(error).__name__}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] == "PASS" else 1

if __name__=="__main__":
    sys.exit(main())
