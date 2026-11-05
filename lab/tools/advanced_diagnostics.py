#!/usr/bin/env python3
"""Offline advanced-Luma diagnostics schema adapter. No fabricated frame timelines.
Advanced src/diagnostics.rs exposes Summary{presented,warmup_frames,pacing,cpu_submission},
each Timing{samples,mean_ms,p95_ms,max_ms}. No p99/raw timeline in source baseline.
"""
from __future__ import annotations
import json
import math
from pathlib import Path

def timing(value: object) -> dict | None:
    if value is None: return None
    if not isinstance(value,dict) or set(value)!={"samples","mean_ms","p95_ms","max_ms"}:
        raise ValueError("unexpected timing schema")
    n=value["samples"]
    if not isinstance(n,int) or isinstance(n,bool) or n<=0:
        raise ValueError("invalid sample count")
    vals=[value[k] for k in ("mean_ms","p95_ms","max_ms")]
    if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0 for v in vals):
        raise ValueError("invalid metric")
    if not vals[0]<=vals[2] or not vals[1]<=vals[2]:
        raise ValueError("inconsistent timing")
    return {**value}

def analyze(report: object) -> dict:
    if not isinstance(report,dict): raise ValueError("summary object required")
    if set(report)!={"presented","warmup_frames","pacing","cpu_submission"}:
        raise ValueError("advanced Luma Summary shape required")
    if any(not isinstance(report[k],int) or isinstance(report[k],bool) or report[k]<0 for k in ("presented","warmup_frames")):
        raise ValueError("bad presented/warmup")
    pacing=timing(report["pacing"])
    cpu=timing(report["cpu_submission"])
    if (pacing is None)!=(cpu is None):
        raise ValueError("pacing and CPU submission sample mismatch")
    if pacing and pacing["samples"]!=cpu["samples"]:
        raise ValueError("different sample counts")
    return {"schema":"luma-advanced-summary-analysis/1","status":"ANALYZED" if pacing else "INSUFFICIENT_SAMPLES",
       "evidence":"INPUT_ONLY_NOT_REMEASURED","presented":report["presented"],
       "warmup_frames":report["warmup_frames"],"pacing":pacing,"cpu_submission":cpu,
       "p99_ms":None,"timeline":None,"input_to_visible_ms":None,"gpu_time_ms":None,"gpu_memory_bytes":None,
       "reason":"advanced fork summary has only aggregate p95 and max, no timeline or GPU data"}

def main() -> int:
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("report",type=Path)
    args=ap.parse_args()
    try: print(json.dumps(analyze(json.loads(args.report.read_text())),indent=2,sort_keys=True));return 0
    except (OSError,ValueError,TypeError,json.JSONDecodeError) as e:
        print(json.dumps({"status":"FAIL","error":type(e).__name__}));return 1
if __name__=="__main__":
    raise SystemExit(main())
