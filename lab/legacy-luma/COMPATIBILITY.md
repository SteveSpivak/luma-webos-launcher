# Legacy Python test compatibility

Historical tests were copied exactly from `SteveSpivak/lg-luma` at `1bef7968` with verified original blob SHAs. One test imports `research.scripts.analyze_native_diagnostics` from the old repository's directory layout. We **did not alter** either historical test or tool to repair the import.

For only these legacy unit tests, use:

```sh
PYTHONPATH=lab/legacy-luma/compat python3 -m unittest discover -s lab/legacy-luma/tests -p 'test_*.py' -v
```

`lab/legacy-luma/compat/research/scripts/analyze_native_diagnostics.py` is a narrow import shim that points to the original copied module and has no device/network execution. The advanced fork uses a different diagnostics schema; for current reports use `lab/tools/advanced_diagnostics.py` instead. Never infer from the historical tests that a native GPU/TV result has been measured.
