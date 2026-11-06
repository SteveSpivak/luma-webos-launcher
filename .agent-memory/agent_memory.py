#!/usr/bin/env python3
"""stdlib-only multi-agent memory/task coordination for Luma.

Agents: Arena (cloud), Claude, Codex, Kimi (local).
Shared append-only logs + SQLite WAL memory store + workspace snapshot.
No cross-agent mutations: each agent appends; reads are consistent snapshots.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TASKS_FILE = BASE_DIR / "tasks.jsonl"
LESSONS_FILE = BASE_DIR / "lessons.jsonl"
MEMORIES_DB = BASE_DIR / "memories.db"
WORKSPACE_FILE = BASE_DIR / "workspace-state.json"

_lock = threading.RLock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# TaskLog — append-only JSONL
# ---------------------------------------------------------------------------
class TaskLog:
    """Append-only task ledger. Each line is a JSON task record."""

    def __init__(self, path: Path = TASKS_FILE) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(
        self,
        task_id: str,
        title: str,
        status: str = "open",
        owner: str | None = None,
        depends_on: list[str] | None = None,
        detail: str = "",
    ) -> dict:
        record = {
            "id": task_id,
            "title": title,
            "status": status,
            "owner": owner,
            "depends_on": depends_on or [],
            "detail": detail,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        with _lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, separators=(",", ":")) + "\n")
        return record

    def list(self) -> list[dict]:
        records: list[dict] = []
        if not self.path.exists():
            return records
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def update_status(self, task_id: str, status: str, owner: str | None = None) -> bool:
        records = self.list()
        changed = False
        for rec in records:
            if rec["id"] == task_id:
                rec["status"] = status
                rec["updated_at"] = _now_iso()
                if owner is not None:
                    rec["owner"] = owner
                changed = True
        if changed:
            self._rewrite(records)
        return changed

    def claim(self, task_id: str, owner: str) -> bool:
        return self.update_status(task_id, "claimed", owner)

    def done(self, task_id: str) -> bool:
        return self.update_status(task_id, "done")

    def _rewrite(self, records: list[dict]) -> None:
        tmp = self.path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
        os.replace(tmp, self.path)

    def next_open(self) -> dict | None:
        for rec in self.list():
            if rec["status"] == "open":
                return rec
        return None


# ---------------------------------------------------------------------------
# LessonLog — append-only JSONL
# ---------------------------------------------------------------------------
class LessonLog:
    """Append-only lesson ledger. Each line is a JSON lesson record."""

    def __init__(self, path: Path = LESSONS_FILE) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(
        self,
        lesson_id: str,
        module: str,
        summary: str,
        detail: str = "",
        severity: str = "info",
    ) -> dict:
        record = {
            "id": lesson_id,
            "module": module,
            "summary": summary,
            "detail": detail,
            "severity": severity,
            "created_at": _now_iso(),
        }
        with _lock:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, separators=(",", ":")) + "\n")
        return record

    def list(self) -> list[dict]:
        records: list[dict] = []
        if not self.path.exists():
            return records
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records


# ---------------------------------------------------------------------------
# MemoryStore — SQLite WAL key-value memory
# ---------------------------------------------------------------------------
class MemoryStore:
    """SQLite WAL memory store. Agents write (key, value, namespace) tuples."""

    def __init__(self, path: Path = MEMORIES_DB) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                key      TEXT PRIMARY KEY,
                value    TEXT NOT NULL,
                namespace TEXT NOT NULL DEFAULT 'general',
                updated_at TEXT NOT NULL
            )
        """
        )
        self._conn.commit()

    def set(self, key: str, value: str, namespace: str = "general") -> None:
        with _lock:
            self._conn.execute(
                "INSERT INTO memories(key, value, namespace, updated_at) "
                "VALUES(?, ?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
                "namespace=excluded.namespace, updated_at=excluded.updated_at",
                (key, value, namespace, _now_iso()),
            )
            self._conn.commit()

    def get(self, key: str, namespace: str = "general") -> str | None:
        with _lock:
            cur = self._conn.execute(
                "SELECT value FROM memories WHERE key=? AND namespace=?",
                (key, namespace),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def query(self, namespace: str = "general") -> list[tuple[str, str]]:
        with _lock:
            cur = self._conn.execute(
                "SELECT key, value FROM memories WHERE namespace=? ORDER BY key",
                (namespace,),
            )
            return [(r[0], r[1]) for r in cur.fetchall()]

    def close(self) -> None:
        with _lock:
            self._conn.close()


# ---------------------------------------------------------------------------
# WorkspaceState — JSON snapshot
# ---------------------------------------------------------------------------
class WorkspaceState:
    """Single-writer JSON snapshot of the workspace: branch, head_sha, CI state, blocks."""

    def __init__(self, path: Path = WORKSPACE_FILE) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def set(
        self,
        branch: str | None = None,
        head_sha: str | None = None,
        ci_rust: str | None = None,
        ci_docs: str | None = None,
        blocked_on: str | None = None,
    ) -> dict:
        state = self.get()
        if branch is not None:
            state["branch"] = branch
        if head_sha is not None:
            state["head_sha"] = head_sha
        if ci_rust is not None:
            state["ci_rust"] = ci_rust
        if ci_docs is not None:
            state["ci_docs"] = ci_docs
        if blocked_on is not None:
            state["blocked_on"] = blocked_on
        state["updated_at"] = _now_iso()
        with _lock:
            tmp = self.path.with_suffix(".json.tmp")
            with tmp.open("w", encoding="utf-8") as fh:
                json.dump(state, fh, indent=2)
            os.replace(tmp, self.path)
        return state

    def get(self) -> dict:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as fh:
            return json.load(fh)


# ---------------------------------------------------------------------------
# AgentRegistry — agent identity
# ---------------------------------------------------------------------------
class AgentRegistry:
    """Known agents that can claim tasks and write memories."""

    def __init__(self) -> None:
        self.agents: list[str] = ["arena", "claude", "codex", "kimi"]

    def register(self, name: str) -> None:
        if name not in self.agents:
            self.agents.append(name)

    def known(self, name: str) -> bool:
        return name in self.agents


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def cmd_task_add(args: argparse.Namespace) -> int:
    log = TaskLog()
    task_id = args.id or f"T-{uuid.uuid4().hex[:8].upper()}"
    rec = log.add(
        task_id=task_id,
        title=args.title,
        status=args.status,
        owner=args.owner,
        depends_on=args.depends_on.split(",") if args.depends_on else None,
        detail=args.detail,
    )
    print(json.dumps(rec, indent=2))
    return 0


def cmd_task_list(_args: argparse.Namespace) -> int:
    log = TaskLog()
    for rec in log.list():
        print(json.dumps(rec, separators=(",", ":")))
    return 0


def cmd_task_claim(args: argparse.Namespace) -> int:
    log = TaskLog()
    ok = log.claim(args.id, args.owner)
    print(json.dumps({"ok": ok, "id": args.id, "owner": args.owner}))
    return 0 if ok else 1


def cmd_task_next(_args: argparse.Namespace) -> int:
    log = TaskLog()
    rec = log.next_open()
    if rec is None:
        print("no open tasks")
        return 0
    print(json.dumps(rec, indent=2))
    return 0


def cmd_task_done(args: argparse.Namespace) -> int:
    log = TaskLog()
    ok = log.done(args.id)
    print(json.dumps({"ok": ok, "id": args.id}))
    return 0 if ok else 1


def cmd_lesson_add(args: argparse.Namespace) -> int:
    log = LessonLog()
    rec = log.add(
        lesson_id=args.id,
        module=args.module,
        summary=args.summary,
        detail=args.detail,
        severity=args.severity,
    )
    print(json.dumps(rec, indent=2))
    return 0


def cmd_memory_add(args: argparse.Namespace) -> int:
    store = MemoryStore()
    store.set(args.key, args.value, args.namespace)
    print(json.dumps({"ok": True, "key": args.key, "namespace": args.namespace}))
    return 0


def cmd_memory_query(args: argparse.Namespace) -> int:
    store = MemoryStore()
    rows = store.query(args.namespace)
    for key, value in rows:
        print(f"{key}\t{value}")
    return 0


def cmd_memory_get(args: argparse.Namespace) -> int:
    store = MemoryStore()
    value = store.get(args.key, args.namespace)
    if value is None:
        print(json.dumps({"ok": False, "key": args.key}))
        return 1
    print(json.dumps({"ok": True, "key": args.key, "value": value}))
    return 0


def cmd_state_set(args: argparse.Namespace) -> int:
    ws = WorkspaceState()
    state = ws.set(
        branch=args.branch,
        head_sha=args.head_sha,
        ci_rust=args.ci_rust,
        ci_docs=args.ci_docs,
        blocked_on=args.blocked_on,
    )
    print(json.dumps(state, indent=2))
    return 0


def cmd_state_get(_args: argparse.Namespace) -> int:
    ws = WorkspaceState()
    print(json.dumps(ws.get(), indent=2))
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    registry = AgentRegistry()
    registry.register(args.name)
    print(json.dumps({"ok": True, "agent": args.name}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-memory", description="Multi-agent memory/task coordination")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("task", help="task log commands")
    tsub = p.add_subparsers(dest="action", required=True)
    pa = tsub.add_parser("add", help="append a task")
    pa.add_argument("--id", default=None)
    pa.add_argument("--title", required=True)
    pa.add_argument("--status", default="open")
    pa.add_argument("--owner", default=None)
    pa.add_argument("--depends-on", default=None)
    pa.add_argument("--detail", default="")
    pa.set_defaults(func=cmd_task_add)
    pl = tsub.add_parser("list", help="list all tasks")
    pl.set_defaults(func=cmd_task_list)
    pc = tsub.add_parser("claim", help="claim a task")
    pc.add_argument("id")
    pc.add_argument("--owner", required=True)
    pc.set_defaults(func=cmd_task_claim)
    pn = tsub.add_parser("next", help="show next open task")
    pn.set_defaults(func=cmd_task_next)
    pd = tsub.add_parser("done", help="mark a task done")
    pd.add_argument("id")
    pd.set_defaults(func=cmd_task_done)

    p = sub.add_parser("lesson", help="lesson log commands")
    lsub = p.add_subparsers(dest="action", required=True)
    la = lsub.add_parser("add", help="append a lesson")
    la.add_argument("--id", required=True)
    la.add_argument("--module", required=True)
    la.add_argument("--summary", required=True)
    la.add_argument("--detail", default="")
    la.add_argument("--severity", default="info")
    la.set_defaults(func=cmd_lesson_add)

    p = sub.add_parser("memory", help="memory store commands")
    msub = p.add_subparsers(dest="action", required=True)
    ma = msub.add_parser("add", help="store a memory")
    ma.add_argument("--key", required=True)
    ma.add_argument("--value", required=True)
    ma.add_argument("--namespace", default="general")
    ma.set_defaults(func=cmd_memory_add)
    mq = msub.add_parser("query", help="query memories by namespace")
    mq.add_argument("--namespace", default="general")
    mq.set_defaults(func=cmd_memory_query)
    mg = msub.add_parser("get", help="get a single memory")
    mg.add_argument("key")
    mg.add_argument("--namespace", default="general")
    mg.set_defaults(func=cmd_memory_get)

    p = sub.add_parser("state", help="workspace state")
    ssub = p.add_subparsers(dest="action", required=True)
    ss = ssub.add_parser("set", help="set workspace state")
    ss.add_argument("--branch", default=None)
    ss.add_argument("--head-sha", dest="head_sha", default=None)
    ss.add_argument("--ci-rust", dest="ci_rust", default=None)
    ss.add_argument("--ci-docs", dest="ci_docs", default=None)
    ss.add_argument("--blocked-on", dest="blocked_on", default=None)
    ss.set_defaults(func=cmd_state_set)
    sg = ssub.add_parser("get", help="get workspace state")
    sg.set_defaults(func=cmd_state_get)

    p = sub.add_parser("register", help="register an agent")
    p.add_argument("name")
    p.set_defaults(func=cmd_register)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
