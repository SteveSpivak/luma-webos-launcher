#!/usr/bin/env python3
"""Pure offline, profile-isolated launcher Continue Watching fixture validator.
No server, credential, network or real account access. Feed producer NOT IMPLEMENTED.
"""
from __future__ import annotations
from datetime import datetime, timezone
from nuvio_launch_contract import build_launch

def timestamp(v: object) -> datetime:
    if not isinstance(v,str) or not v.endswith("Z"):
        raise ValueError("UTC Z timestamp required")
    try:
        d=datetime.fromisoformat(v.replace("Z","+00:00"))
    except ValueError as e:
        raise ValueError("invalid time") from e
    if d.tzinfo is None or d.utcoffset().total_seconds()!=0:
        raise ValueError("non UTC")
    return d

def validate_feed(feed: object, current_profile: str, now_iso: str,
                  expected_revision: int | None = None) -> list[dict]:
    if not isinstance(feed,dict) or set(feed)!={"schema","revision","generated_at","profile_alias","items"}:
        raise ValueError("unrecognized feed shape")
    if feed["schema"]!="nuvio.launcher.cw.v1":
        raise ValueError("unsupported schema")
    if not isinstance(feed["revision"],int) or isinstance(feed["revision"],bool) or feed["revision"]<1:
        raise ValueError("bad revision")
    if expected_revision is not None and feed["revision"]<expected_revision:
        raise ValueError("stale generation")
    if not isinstance(current_profile,str) or not current_profile or feed["profile_alias"]!=current_profile:
        raise ValueError("profile mismatch")
    age=(timestamp(now_iso)-timestamp(feed["generated_at"])).total_seconds()
    if not 0<=age<=300:
        raise ValueError("expired/future feed")
    rows=feed["items"]
    if not isinstance(rows,list) or len(rows)>20:
        raise ValueError("unbounded or invalid item list")
    seen=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"type","source","source_id","title","progress_seconds","duration_seconds","artwork_ref","updated_at"}:
            raise ValueError("unexpected content fields")
        build_launch(row["type"],row["source"],row["source_id"])
        key=(row["type"],row["source"],row["source_id"])
        if key in seen:
            raise ValueError("duplicate title")
        seen.add(key)
        if not isinstance(row["title"],str) or not 1<=len(row["title"])<=140:
            raise ValueError("bad title")
        if not isinstance(row["artwork_ref"],str) or not row["artwork_ref"].startswith("opaque:") or len(row["artwork_ref"])>90 or any(c in row["artwork_ref"] for c in ("/","\\","?","#","@")):
            raise ValueError("artwork must be opaque reference, not URL")
        seconds=row["progress_seconds"]; duration=row["duration_seconds"]
        if any(not isinstance(x,(int,float)) or isinstance(x,bool) for x in (seconds,duration)) or not (0<=seconds<=duration and 0<duration<=86400):
            raise ValueError("invalid progress")
        if timestamp(row["updated_at"])>timestamp(now_iso):
            raise ValueError("future item")
    return rows

class ProfileCache:
    def __init__(self):
        self.profile=None
        self.revision=0
        self.items=[]
    def switch_profile(self,profile: str | None):
        if profile!=self.profile:
            self.profile=profile
            self.revision=0
            self.items=[]
    def accept(self,feed: dict,now_iso: str):
        if not self.profile:
            raise ValueError("no profile selected")
        self.items=validate_feed(feed,self.profile,now_iso,self.revision)
        self.revision=feed["revision"]
