# Evidence and self-containment audit — 2026-11-05

The main advanced Luma application, locked dependencies and CI are inherited directly from upstream at `40994fc1`. The `lab/` additions are **real committed executable files**, not external references. None reaches the TV.

## Actual portable files

- `lab/tools/kit_verify.py`: pinned Git blob-hash integrity and tampering checks.
- `lab/tools/nuvio_launch_contract.py`: restrictive outbound Nuvio title request builder/validator.
- `lab/tools/mock_webos_nuvio.py`: simulated application manager, login/profile-ready/relaunch, duplicate/Back, error codes.
- `lab/tools/cw_fixture.py`: proposed feed validator, profile isolation, freshness/generation and offline cache fixture.
- `lab/tools/advanced_diagnostics.py`: works with the **actual advanced Luma** `src/diagnostics.rs` aggregate schema; does not invent absent p99 or GPU stats.
- `lab/tests/test_kit.py`, `lab/tests/test_integration_harness.py`: offline tests and negative cases.
- `lab/fixtures/*.json`: synthetic sample feed and diagnostics input.
- `lab/legacy-luma/scripts/` plus tests: selected historical tools, pinned via source SHA.
- `lab/references/lg-luma/`: copied historic forensic architecture/perf/video reports, pinned.
- `.github/workflows/arena-lab.yml`: checks Python tools against the actual PR checkout, no root/TV/network scripts or dependencies; actions/checkout fetches only the Git repository.

## Scope and limitations
1. This is self-contained **for Luma source and first outbound Nuvio launch implementation**, and for mock testing. The private Nuvio service/Continue Watching implementation is **not** in this public repo. The feed schema is proposed, not an existing export. Live integration cannot be achieved from mock evidence alone.
2. The simulator is a falsifiable model: Nuvio's exact timing/back behavior on TV is NOT_RUN. Its last-request-wins and profile-clearing behavior are proposals, not claims about deployed Nuvio.
3. Advanced diagnostics currently records only aggregate pacing p95, max and CPU-submission summaries. New p99/input trace would require instrumented code changes under separate test gates, not arithmetic from absent samples.
4. GitHub source hash receipts prove bytes copied, not that copied scripts work against the advanced fork; they are historical and not runtime imports.
5. Real TV app identity must be distinct from `com.denisefremov.luma` before any physical canary. Nuvio title navigation and Back must be observed on actual installed app only with approval.

## Portable verification
```sh
python3 lab/tools/kit_verify.py
python3 -m unittest discover -s lab/tests -p 'test_*.py' -v
python3 -m unittest discover -s lab/legacy-luma/tests -p 'test_*.py' -v
python3 -m compileall -q lab/tools lab/tests lab/legacy-luma
```

These tests are automatically attempted by the new PR workflow. See the PR checks for actual results, not agent prose. If CI is blocked, mark TESTS NOT_RUN.
