"""Tests for luma_cli.py: the single read-only orientation entrypoint.

These exercise the CLI's own logic (protected-path classification, the math
dispatcher, the facts-file status mapping, and the generic blob-diff helper)
with hand-picked or hand-computed expectations. They do not build anything
native, install anything, or contact a device.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "research/scripts"
sys.path.insert(0, str(SCRIPTS))

import luma_cli  # noqa: E402
import reference_launcher as physics  # noqa: E402
from protected_paths import PREFIXES, FILES, is_protected  # noqa: E402


def run_json(args: list[str]) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, "-B", str(SCRIPTS / "luma_cli.py"), *args],
                           cwd=ROOT, capture_output=True, text=True, timeout=60)
    return proc.returncode, (json.loads(proc.stdout) if proc.stdout.strip() else {})


class ProtectedPathTests(unittest.TestCase):
    def test_known_examples_are_classified_correctly(self):
        protected_examples = ["src/main.rs", "appinfo.json", "Cargo.toml", "Cargo.lock",
                               "package.json", "tv/view.rs", "tests/focus_test.rs",
                               "vector-geometry/lib.rs", "assets/fonts/Inter.ttf", "tools/sync.mjs"]
        unprotected_examples = ["README.md", "research/scripts/luma_cli.py",
                                 "delivery/HANDOFF.md", ".github/workflows/ci.yml", "flake.nix"]
        for path in protected_examples:
            self.assertTrue(is_protected(path), f"{path} should be protected")
        for path in unprotected_examples:
            self.assertFalse(is_protected(path), f"{path} should not be protected")

    def test_matches_the_literal_audit_definition(self):
        # Must stay byte-identical to the list build_audit.py used before the
        # extraction, or the two gates could silently diverge.
        legacy_prefixes = ('src/', 'tv-helper/', 'tv/', 'vector-geometry/', 'assets/', 'tools/', 'tests/')
        legacy_files = ('Cargo.toml', 'Cargo.lock', 'package.json', 'appinfo.json')
        self.assertEqual(PREFIXES, legacy_prefixes)
        self.assertEqual(FILES, legacy_files)


class MathDispatchTests(unittest.TestCase):
    def _call(self, op, args=(), kw=()):
        ns = argparse.Namespace(op=op, args=list(args), kw=list(kw), list=False)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = luma_cli.cmd_math(ns)
        return exit_code, json.loads(buf.getvalue())

    def test_shadow_quad_matches_direct_call(self):
        exit_code, payload = self._call("shadow_quad", args=["256", "154.4", "34"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["result"], physics.shadow_quad(256.0, 154.4, 34.0))
        self.assertIn("MODEL", payload["label"])

    def test_keyword_arguments_are_parsed_and_applied(self):
        exit_code, payload = self._call("pop_peak", kw=["decay=5", "freq=10"])
        self.assertEqual(exit_code, 0)
        self.assertAlmostEqual(payload["result"], physics.pop_peak(decay=5.0, freq=10.0))

    def test_unknown_function_is_a_clean_error_not_a_crash(self):
        # Reported on stderr, not stdout as JSON, so call cmd_math directly.
        ns = argparse.Namespace(op="definitely_not_a_real_function", args=[], kw=[], list=False)
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            exit_code = luma_cli.cmd_math(ns)
        self.assertEqual(exit_code, 2)
        self.assertIn("unknown function", buf.getvalue())

    def test_invalid_arguments_are_reported_not_raised(self):
        # contrast() raises ValueError for a non-positive offset; the CLI must
        # surface that as a clean exit 2, not an uncaught traceback.
        exit_code, payload = self._call("contrast", args=["34", "0"])
        self.assertEqual(exit_code, 2)
        self.assertIn("error", payload)

    def test_catalog_lists_every_public_function_once(self):
        ns = argparse.Namespace(op=None, args=[], kw=[], list=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            luma_cli.cmd_math(ns)
        payload = json.loads(buf.getvalue())
        expected = {name for name, fn in vars(physics).items()
                    if callable(fn) and not name.startswith("_") and fn.__module__ == physics.__name__}
        self.assertEqual(set(payload["functions"]), expected)
        self.assertGreater(len(expected), 15)


class ComponentsFactsConsistencyTests(unittest.TestCase):
    def test_reported_bucket_counts_match_the_committed_facts_file(self):
        facts_path = ROOT / "research/audit/reference-launcher-facts.json"
        if not facts_path.exists():
            self.skipTest("no pinned reference facts in this checkout")
        facts = json.loads(facts_path.read_text())
        expected = {"shared": 0, "only_ours": 0, "only_reference": 0}
        bucket_of = {"both": "shared", "only_ours": "only_ours", "only_reference": "only_reference"}
        for component in facts["components"]:
            expected[bucket_of[component["status"]]] += 1

        exit_code, payload = run_json(["components"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["pinned_reference_comparison"]["component_counts"], expected)


class DocsArchitectureTests(unittest.TestCase):
    def test_this_checkout_has_no_broken_relative_doc_links(self):
        exit_code, payload = run_json(["docs"])
        self.assertEqual(payload["broken_links"], [])
        self.assertEqual(exit_code, 0)
        self.assertGreater(payload["files"], 5)


class ReviewGateTests(unittest.TestCase):
    def test_review_is_clean_against_the_audit_base(self):
        exit_code, payload = run_json(["review"])
        self.assertEqual(payload["protected_clean"], True)
        self.assertEqual(payload["protected_files_changed"], [])
        self.assertEqual(exit_code, 0)


class BlobDiffTests(unittest.TestCase):
    """blob_diff() is tested against two tiny synthetic repos, not the real
    checkout, so every count below is hand-verifiable from the setup."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ours = self._make_repo("ours", {
            "shared_identical.txt": "same bytes\n",
            "shared_changed.txt": "ours version\n",
            "only_ours.txt": "unique to ours\n",
        })
        self.theirs = self._make_repo("theirs", {
            "shared_identical.txt": "same bytes\n",
            "shared_changed.txt": "theirs version\n",
            "only_theirs.txt": "unique to theirs\n",
        })

    def _make_repo(self, name: str, files: dict) -> Path:
        repo = Path(self._tmp.name) / name
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        for rel, content in files.items():
            (repo / rel).write_text(content)
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=repo, check=True)
        return repo

    def test_shared_identical_and_changed_counts_are_exact(self):
        result = luma_cli.blob_diff(self.ours, "HEAD", self.theirs, expected_external_rev=None)
        self.assertEqual(result["files_ours"], 3)
        self.assertEqual(result["files_external"], 3)
        self.assertEqual(result["shared_paths"], 2)
        self.assertEqual(result["identical_blobs"], 1)
        self.assertEqual(result["changed_blobs"], 1)
        self.assertEqual(result["only_ours"], 1)
        self.assertEqual(result["only_external"], 1)

    def test_pinned_rev_mismatch_is_refused(self):
        with self.assertRaises(ValueError):
            luma_cli.blob_diff(self.ours, "HEAD", self.theirs, expected_external_rev="0" * 40)

    def test_non_git_directory_is_refused(self):
        not_a_repo = Path(self._tmp.name) / "plain"
        not_a_repo.mkdir()
        with self.assertRaises(ValueError):
            luma_cli.blob_diff(self.ours, "HEAD", not_a_repo, expected_external_rev=None)


if __name__ == "__main__":
    unittest.main()
