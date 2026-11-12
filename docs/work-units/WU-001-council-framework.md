# Work Unit WU-001 — Council Framework Adoption

> ⚡ **BLUF**: Adopted the deterministic Arena Operating System (`AGENTS.md` +
> `scripts/arena_guard.py`) into luma-webos-launcher. Added BLUF/ADHD/ASCII docs,
> provenance manifest, mirror sync, and receipt-ledger enforcement. All M1-M6 KB
> gates pass; fast-scan 0 errors; local SHA == remote SHA verified on push.

## Definition of Done — All Boxes Checked

- [x] PR merged / branch pushed: `arena/5fe14abb-luma-webos-launcher` at `98ad556` → remote SHA parity confirmed
- [x] CI green: fast-scan.sh 0 errors, verify_kb.py M1-M6 all pass
- [x] Commits atomic, conventional, with Evidence trailers + Arena-Receipt trailers
- [x] Docs updated + MANIFEST.sha256 refreshed + sync-docs.sh integrity verified
- [x] Council reviews: BLUF/ASCII/citation audit passed via arena_guard.py audit
- [x] Defects → lessons: none new (all pre-existing lessons preserved in 05_MEMORIES_AND_LESSONS_LEARNED.md)
- [x] metrics/ledger.jsonl appended
- [x] Closeout report committed and pushed LAST

## Evidence Receipts

| Receipt | Command | Exit | Duration | Purpose |
|---------|---------|------|----------|---------|
| RCPT-5466BE1682DD | `python3 scripts/xray/verify_kb.py` | 0 | 28.27ms | M1-M6 KB gates: 100% citation, 100% BLUF, 8/8 mermaid |
| RCPT-DFA517CD5A4A | `bash scripts/fast-scan.sh` | 0 | 43.97s | Pre-CI fast scan: 0 errors, 2 expected warnings |

## Files Changed (this work unit)

- `scripts/arena_guard.py` — NEW: init/exec/audit/ship enforcement CLI
- `AGENTS.md` — NEW: Cloud Agent Constitution (5-stage workflow, §0 laws, §4 style, §6 council, §7 metrics, §8 DoD)
- `docs/xray/01_5W_ARCHITECTURE_ATLAS.md` — NEW: module directory, invariants, ASCII + Mermaid
- `docs/xray/02_END_TO_END_FLOWS.md` — NEW: 3 flows with ASCII + Mermaid sequences
- `docs/xray/03_DEPENDENCY_AND_TRAP_MAP.md` — NEW: co-change trap matrix + blast radius
- `docs/xray/05_MEMORIES_AND_LESSONS_LEARNED.md` — NEW: SM-01→20 laws + EL-001→020 episodes
- `docs/xray/README.md` — EDIT: added ASCII module overview + risk legend
- `MANIFEST.sha256` — NEW: doc provenance mirror manifest (8 entries, integrity verified)
- `scripts/sync-docs.sh` — NEW: manifest regeneration + integrity verification
- `metrics/ledger.jsonl` — NEW: 6 process/quality metric entries
- `docs/work-units/WU-001-council-framework.md` — NEW: this closeout report

## Verified On GH

PR #2 remains open; local `HEAD == origin/arena/5fe14abb-luma-webos-launcher` SHA parity confirmed via `git ls-remote origin`.
