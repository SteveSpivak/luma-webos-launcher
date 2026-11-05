from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from nuvio_launch_contract import build_launch, validate_launch, parse_untrusted_json
from kit_verify import git_blob_sha, audit

class TestNuvioLaunch(unittest.TestCase):
    def test_movie_and_series(self):
        a=build_launch("movie","tmdb","603")
        b=build_launch("series","imdb","tt0903747")
        self.assertEqual(a["params"]["contentTarget"],"nuvio://tmdb/movie/603")
        self.assertEqual(b["params"]["contentTarget"],"nuvio://imdb/series/tt0903747")
        self.assertEqual(validate_launch(a),a)
        self.assertEqual(parse_untrusted_json(json.dumps(b)),b)
    def test_invalid_inputs_rejected(self):
        for args in [("tv","tmdb","603"),("movie","unknown","603"),
                     ("movie","tmdb","../../../etc/passwd"),("movie","tmdb",""),
                     ("movie","tmdb","https://bad"),("series","imdb","tt2")]:
            with self.subTest(args=args),self.assertRaises(ValueError):
                build_launch(*args)
    def test_unknown_app_and_side_effect_params_rejected(self):
        valid=build_launch("movie","tmdb","603")
        for item in [{**valid,"id":"com.webos.app.home"},
                     {**valid,"params":{"contentTarget":"nuvio://tmdb/movie/603","autoplay":True}},
                     {**valid,"params":{"contentTarget":"https://example.com"}},
                     {"id":"space.nuvio.webos","params":{"contentTarget":"nuvio://tmdb/movie/603"},"service":"exec"}]:
            with self.subTest(item=item),self.assertRaises(ValueError):
                validate_launch(item)
    def test_invalid_json_and_overlong_rejected(self):
        for raw in ["{", "[]", "x"*513, '{"id":"space.nuvio.webos","params":{"contentTarget":"nuvio://imdb/movie/xx"}}']:
            with self.subTest(raw=raw[:30]),self.assertRaises((ValueError,json.JSONDecodeError)):
                parse_untrusted_json(raw)

class TestReferenceIntegrity(unittest.TestCase):
    def test_git_blob_known_fixture(self):
        self.assertEqual(git_blob_sha(b"test content\n"),"d670460b4b4aece5915caf5c68d12f560a9fe3e4")
    def test_manifest_rejects_corrupt_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"lab").mkdir()
            (root/"lab/demo.txt").write_text("ok")
            record={"schema":"luma-nuvio-reference-import/1","source_commit":"test",
                    "files":[{"target_path":"lab/demo.txt","source_blob_sha":git_blob_sha(b"ok")}]}
            manifest=root/"manifest.json"
            manifest.write_text(json.dumps(record))
            self.assertEqual(audit(root,manifest)["status"],"PASS")
            (root/"lab/demo.txt").write_text("bad")
            self.assertEqual(audit(root,manifest)["status"],"FAIL")
            (root/"lab/demo.txt").unlink()
            self.assertEqual(audit(root,manifest)["files"][0]["status"],"MISSING_OR_SYMLINK")
    def test_manifest_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            m=root/"manifest.json"
            m.write_text(json.dumps({"schema":"luma-nuvio-reference-import/1","source_commit":"test",
              "files":[{"target_path":"../unsafe","source_blob_sha":"0"*40}]}))
            with self.assertRaises(ValueError):audit(root,m)
if __name__=="__main__":unittest.main()
