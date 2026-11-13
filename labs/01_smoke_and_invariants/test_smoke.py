#!/usr/bin/env python3
"""Lab 01 smoke test — trivial deterministic test for hyper_runner Merkle-DAG demo."""
import unittest


class SmokeInvariants(unittest.TestCase):
    def test_python_version_is_supported(self):
        import sys
        self.assertGreaterEqual(sys.version_info, (3, 8))

    def test_hyper_cache_dir_exists(self):
        from pathlib import Path
        import os
        root = Path(os.environ.get("REPO_ROOT", ".")).resolve()
        self.assertTrue((root / "scripts" / "hyper_runner.py").exists())


if __name__ == "__main__":
    unittest.main()
