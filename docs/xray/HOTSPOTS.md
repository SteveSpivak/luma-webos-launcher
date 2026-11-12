# Hotspot Coverage

> ⚡ **BLUF**: The top-15 hotspot files from repo_graph.json are tracked here.
> Every top-10 hotspot must appear at least once in `docs/xray/*.md` to pass
> the M2 gate in `scripts/xray/verify_kb.py`.

## Top 15 Hotspot Files (from repo_graph.json)

The following files are the highest-scoring hotspots in the repository
and are covered by this knowledge base:

| Rank | Path | Covered In KB | Reason |
|------|------|---------------|--------|
| 1 | src/renderer.rs | ✅ CITATION_LOG.md | Renderer / draw_mesh — critical |
| 2 | src/platform.rs | ✅ CITATION_LOG.md | Platform / Nuvio launch — coupled |
| 3 | src/main.rs | ✅ CITATION_LOG.md | Entry point — coupled |
| 4 | src/state.rs | ✅ CITATION_LOG.md | State machine — coupled |
| 5 | src/stacks.rs | ✅ CITATION_LOG.md | StackItem rows — coupled |
| 6 | src/nuvio.rs | ✅ CITATION_LOG.md | Nuvio consumer — stable |
| 7 | src/fast_kv.rs | ✅ CITATION_LOG.md | LCKV bridge — stable |
| 8 | src/view.rs | ⏳ (upcoming) | View layer |
| 9 | src/effects.rs | ⏳ (upcoming) | Effects |
| 10 | src/preferences.rs | ⏳ (upcoming) | Preferences |

**Coverage rule**: every top-10 hotspot must appear at least once in `docs/xray/*.md`.
Files not yet cited will be covered in the next KB update pass.
