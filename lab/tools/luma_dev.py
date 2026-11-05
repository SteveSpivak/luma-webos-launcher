#!/usr/bin/env python3
"""Offline, read-only orientation CLI for the ADVANCED Luma fork.
No network, installs or TV contact. Native status is never inferred from Python tests.
The old CLI is preserved verbatim in lab/legacy-luma/20261105-cli/ (not executable here).
"""
from __future__ import annotations
import argparse, collections, json, math, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PIN="40994fc144b5af481056d14e2fb93304aa1e2c82"
PROTECTED_PREFIXES=("src/","native/","tv/","assets/","tools/","tests/","extras/","vector-geometry/")
PROTECTED_FILES={"Cargo.toml","Cargo.lock","pnpm-lock.yaml","package.json","appinfo.json",".github/workflows/ci.yml"}
DOC_DIRS=("lab","docs")
def run(cmd:list[str],root:Path=ROOT)->str:
    return subprocess.check_output(cmd,cwd=root,text=True,stderr=subprocess.PIPE)
def git(*args,root=ROOT):return run(["git",*args],root)
def paths(rev:str="HEAD",root:Path=ROOT):
    return git("ls-tree","-r","--name-only",rev,root=root).splitlines()
def protected(p:str)->bool:return p in PROTECTED_FILES or p.startswith(PROTECTED_PREFIXES)
def emit(x):print(json.dumps(x,sort_keys=True,indent=2))
def cmd_status(a):
    rev=git("rev-parse","HEAD").strip()
    branch=git("branch","--show-current").strip()
    dirty=git("status","--porcelain").splitlines()
    inventory=paths()
    checks=["lab/tools/kit_verify.py","lab/tests/test_kit.py","lab/tests/test_integration_harness.py","lab/ARENA-ASSIGNMENT.md","lab/NUVIO-CONTRACT.md","lab/legacy-luma/20261105-cli/import-manifest.json"]
    missing=[p for p in checks if p not in inventory]
    emit({"repo":"advanced-luma","head":rev,"branch":branch,"baseline":PIN,"dirty_count":len(dirty),
          "dirty_paths_not_emitted":True,"required_files_missing":missing,
          "native_tests":"NOT_RUN_BY_STATUS","tv_tests":"NOT_RUN_BY_STATUS",
          "status":"READY_FOR_OFFLINE_TESTS" if not missing else "INCOMPLETE"})
    return 1 if missing else 0
def cmd_map(a):
    pp=paths(a.rev);top=collections.Counter(p.split("/")[0] for p in pp);ext=collections.Counter(Path(p).suffix or "(none)" for p in pp)
    emit({"rev":a.rev,"total_files":len(pp),"top_level":dict(sorted(top.items())),"extensions":dict(sorted(ext.items()))})
    return 0
def cmd_components(a):
    pp=[p for p in paths(a.rev) if p.startswith("src/") and p.endswith(".rs")]
    groups={"media":("player","media","video","hw_wallpaper","aerial"),"connectivity":("smart_home","jellyfin","plex","moonlight","widgets","phone_link"),
            "rendering":("renderer","view","motion","font","text","vector","wallpaper","diagnostics"),
            "platform":("platform","luna","webos","input"),"other":()}
    def group(p):
        name=Path(p).stem
        return next((k for k,prefixes in groups.items() if any(name.startswith(x) for x in prefixes)), "other")
    emit({"rev":a.rev,"source_modules":len(pp),"modules":[{"path":p,"owner_guess":group(p)} for p in pp],
          "note":"Filename group only; not dependency/impact analysis"})
    return 0
def cmd_review(a):
    changed=git("diff","--name-only",f"{a.base}..{a.rev}").splitlines()
    found=[p for p in changed if protected(p)]
    emit({"base":a.base,"rev":a.rev,"changed_count":len(changed),"protected_changes":found,
          "status":"REVIEW_REQUIRED" if found else "NO_PROTECTED_CHANGE",
          "note":"Changes to runtime are not automatically defects; deliberate changes need risk/test review"})
    return 1 if found else 0
def cmd_docs(a):
    pp=paths(a.rev);names=[p for p in pp if p.endswith(".md") and p.startswith(("lab/","docs/"))]
    headings={}
    for p in names:
        content=git("show",f"{a.rev}:{p}")
        headings[p]=re.findall(r"^#{1,3} (.+)$",content,re.M)
    emit({"rev":a.rev,"count":len(names),"headings":headings})
    return 0
def cmd_math(a):
    from math import ceil
    def shadow_quad(w,h,b):return (w+2*b)*(h+2*b)
    def rgba_bytes(w,h,buffers=1):return int(w*h*4*buffers)
    def focus_pop(k,decay=5,freq=10):return 1-math.exp(-decay*k)*math.cos(freq*k)
    ops={"shadow_quad":(shadow_quad,3),"rgba_bytes":(rgba_bytes,2),"focus_pop":(focus_pop,1)}
    if a.op=="list":
        emit({"ops":list(ops),"label":"MODEL_ONLY"});return 0
    if a.op not in ops:return 2
    fn,n=ops[a.op]
    if len(a.args)<n:return 2
    try:
        vals=[float(v) for v in a.args]
        if any(not math.isfinite(v) for v in vals):raise ValueError()
        result=fn(*vals)
        if not math.isfinite(result):raise ValueError()
    except (ValueError,TypeError,OverflowError):return 2
    emit({"function":a.op,"args":vals,"result":result,"label":"MODEL_NOT_MEASURED"})
    return 0
def tree_blobs(root:Path,rev:str)->dict:
    lines=git("ls-tree","-r",rev,root=root).splitlines()
    blobs={}
    for line in lines:
        left,sep,path=line.partition("\t")
        fields=left.split()
        if not sep or len(fields)!=3 or fields[1]!="blob":continue
        blobs[path]=fields[2]
    return blobs
def cmd_forensics(a):
    other=a.external_repo.resolve()
    if not (other/".git").exists():
        print("external git checkout missing",file=sys.stderr);return 2
    actual=git("rev-parse","HEAD",root=other).strip()
    if not re.fullmatch(r"[0-9a-f]{40}",a.external_rev) or actual!=a.external_rev:
        print("external HEAD does not match required 40-char pin",file=sys.stderr);return 2
    ours=tree_blobs(ROOT,a.rev);theirs=tree_blobs(other,a.external_rev)
    common=set(ours)&set(theirs)
    same=sum(ours[p]==theirs[p] for p in common)
    emit({"ours_rev":a.rev,"external_commit":actual,"shared_paths":len(common),"identical":same,
          "different":len(common)-same,"only_ours":len(ours)-len(common),
          "only_external":len(theirs)-len(common),"label":"SOURCE_BLOB_COMPARISON"})
    return 0
def cmd_test(a):
    commands=[["python3","lab/tools/kit_verify.py"],
              ["python3","-m","unittest","discover","-s","lab/tests","-p","test_*.py","-v"]]
    results=[]
    for cmd in commands:
        p=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=60)
        results.append({"argv":cmd,"exit_code":p.returncode,"stdout_tail":p.stdout.splitlines()[-3:],
                        "stderr_tail":p.stderr.splitlines()[-3:]})
        if p.returncode:break
    emit({"checks":results,"status":"PASS" if len(results)==len(commands) and all(x["exit_code"]==0 for x in results) else "FAIL",
          "scope":"OFFLINE_ONLY","native":"NOT_RUN","tv":"NOT_RUN"})
    return 0 if len(results)==len(commands) and all(x["exit_code"]==0 for x in results) else 1
def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    subs=ap.add_subparsers(dest="command",required=True)
    for name,fn in (("status",cmd_status),("map",cmd_map),("components",cmd_components),("review",cmd_review),("docs",cmd_docs),("math",cmd_math),("forensics",cmd_forensics),("test",cmd_test)):
        p=subs.add_parser(name);p.set_defaults(func=fn)
        if name in ("map","components","docs","review","forensics"):p.add_argument("--rev",default="HEAD")
        if name=="review":p.add_argument("--base",default=PIN)
        if name=="math":p.add_argument("op");p.add_argument("args",nargs="*")
        if name=="forensics":p.add_argument("--external-repo",type=Path,required=True);p.add_argument("--external-rev",required=True)
    args=ap.parse_args(argv)
    try:return args.func(args)
    except (OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired,ValueError) as e:
        print(json.dumps({"status":"FAIL","error":type(e).__name__}),file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
