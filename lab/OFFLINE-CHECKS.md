# Offline kit verification: exact commands

No dependency installation and no device access needed for these Python-only tests. Run in the actual checked-out branch and record the exact exit code. This runbook is a **planned test procedure**, not a claim it ran on Arena.

```sh
git rev-parse HEAD
git status --porcelain=v1
python3 lab/tools/kit_verify.py
python3 -m unittest discover -s lab/tests -p 'test_*.py' -v
python3 -m unittest discover -s lab/legacy-luma/tests -p 'test_*.py' -v
```

- `kit_verify.py` recomputes Git object blob hashes (not plain SHA256) against source recorded SHA and rejects missing, changed or symlinked sources. If any copied historical file is deliberately changed, do **not** secretly rewrite the old import manifest; create a new derived script and cite old SHA.
- `nuvio_launch_contract.py` is an **offline restrictive outbound request model** and cannot launch the TV. Nuvio's actual parser accepts more formats. Production code must use existing Rust/Luna app launch with validations.
- Include a known-bad edited file, missing file, traversal and malformed title negative test in receipts. Never publish raw sensitive test output.
- Prior old-Luma diagnostic scripts may expect a different schema. Do not run them on advanced Luma output without a documented adapter and negative tests.
- Record results with actual host/platform and stdout/stderr hashes. Native/TV status remains NOT_RUN until run. 
