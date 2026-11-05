# ARENA START HERE

Target: `SteveSpivak/luma-webos-launcher`. Research branch: `research/arena-nuvio-integration-kit-20261105`. Upstream baseline `40994fc144b5af481056d14e2fb93304aa1e2c82`.

This branch contains: upstream advanced launcher (already forked), 13 exact-version historical Luma reference assets in `lab/`, two stdlib-only offline tools, 3 new test groups with negative cases, source provenance and a complete source-backed Arena integration assignment. **No active runtime feature was added and no TV or native build was executed by this publication step**.

**First:** `AGENTS.md` -> `lab/ARENA-ASSIGNMENT.md` -> `lab/OFFLINE-CHECKS.md`. Read source ledger before requesting any other repo. Implement **Nuvio title-to-detail launch only**, behind default OFF, after baseline tests. Do not infer CW producer, copy private code, or touch TV. The existing motion/widgets/media architecture needs measurement, not wholesale replacement.

Source code still comes from upstream; this research branch should only be merged after review. Any new runtime integration goes on a separate isolated agent branch based on this kit.
