# Advanced Luma developer CLI: imported prior art and adapted owner

**Verified source:** original Arena CLI at `SteveSpivak/lg-luma@cef5c1e76ad8db29ef0f21c2ecb3dfb15b98c205` is copied **verbatim** under `lab/legacy-luma/20261105-cli/`, together with its supporting math, comparison, protected-path file, 13-test module and agent packet. Its absolute old-fork base, manifest paths and patch gates are **not compatible with this advanced fork**.

This repo's current CLI is `lab/tools/luma_dev.py`. It deliberately uses the advanced fork's source pin and `lab/` layout. No installs, downloads or device calls.

```sh
python3 lab/tools/luma_dev.py status
python3 lab/tools/luma_dev.py map
python3 lab/tools/luma_dev.py docs
python3 lab/tools/luma_dev.py components
python3 lab/tools/luma_dev.py review
python3 lab/tools/luma_dev.py math list
python3 lab/tools/luma_dev.py math shadow_quad 256 154.4 42
python3 lab/tools/luma_dev.py test
# only when separate clone and exact SHA already provided:
python3 lab/tools/luma_dev.py forensics --external-repo /path/to/read-only-clone --external-rev <40-hex-sha>
```

**Semantics:** `status` checks presence/inventory, NOT native tests; `test` actually runs the new lab's offline gate; `review` returns 1 if protected code differs from the *advanced baseline* so agent must review source changes; a protected diff is **not inherently a defect**. `math` is a MODEL only. `forensics` counts blob IDs with a pinned already-present clone. `components` uses filenames as owner guesses, not a complete call graph.

**What not to copy from old packet:** `git reset --hard FETCH_HEAD` can destroy dirty work; use stash/worktree isolation and explicit tree/branch recovery first. The old focus-depth patch applies to the old fork and is not portable; don't apply it. Old `build_audit.py` writes under `research/audit` and is pinned to a different base/hand-off: do not run it on this fork.

After agent implementation, run negative tests for app launch, profile/stale CW and protected services. The CLI is support tooling, not implementation of Nuvio integration.
