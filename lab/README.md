# Verified source-backed reference kit

Source: SteveSpivak/lg-luma at immutable commit `1bef79683968841426d89f066bd5bf1c0e3bbe31`. The copied scripts are **offline analysis tools** and paired unit tests. The reference documents are *historical* investigations of a **different fork** (`com.ecklf.luma`); do not treat them as current advanced-launcher implementation or current benchmark results. No production Rust source or package scripts were overwritten. These copies are not an upstream merge.

Run the stdlib-only copied metric analyzer tests from the target root:

```sh
python3 -m unittest discover -s lab/legacy-luma/tests -p 'test_*.py' -v
```

The diagnostics analyzer expects the older fork's `profile.timeline`; on this advanced fork a different diagnostics schema may exist, so first inspect and adapt via *new* code/tests rather than changing or mislabeling historical results. `receipt.py` writes raw command outputs outside the checkout and does not sanitize secrets; **use only for pre-approved, non-sensitive offline tests**.

See `lab/reference-import-manifest.json` for per-file source Git blob SHA, then `lab/ARENA-ASSIGNMENT.md` for the actual work. Cross-repo Nuvio and LG-TV code is **not copied** because those source repos are private and this target repo is public; only non-secret contracts and pinned references are included in the new docs.
