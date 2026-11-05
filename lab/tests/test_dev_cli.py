from __future__ import annotations
import importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/"lab/tools/luma_dev.py"
spec=importlib.util.spec_from_file_location("luma_dev",SCRIPT)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class DevCLI(unittest.TestCase):
    def cli(self,*args):
        return subprocess.run([sys.executable,str(SCRIPT),*args],cwd="/tmp",text=True,capture_output=True)
    def test_status_from_unrelated_cwd(self):
        x=self.cli("status");self.assertEqual(x.returncode,0,x.stderr)
        j=json.loads(x.stdout);self.assertIn(j["status"],("READY_FOR_OFFLINE_TESTS",))
        self.assertEqual(j["tv_tests"],"NOT_RUN_BY_STATUS")
    def test_components_and_map(self):
        for operation,key in (("map","total_files"),("components","source_modules"),("docs","count")):
            x=self.cli(operation);self.assertEqual(x.returncode,0,x.stderr);self.assertIn(key,json.loads(x.stdout))
    def test_review_protected_classification(self):
        self.assertTrue(mod.protected("src/platform.rs"))
        self.assertTrue(mod.protected("native/smp/foo.c"))
        self.assertTrue(mod.protected("appinfo.json"))
        self.assertFalse(mod.protected("lab/NUVIO-CONTRACT.md"))
        x=self.cli("review");self.assertEqual(x.returncode,0,x.stderr)
        self.assertEqual(json.loads(x.stdout)["protected_changes"],[])
    def test_model_and_negative_math(self):
        x=self.cli("math","shadow_quad","256","154.4","42")
        self.assertEqual(x.returncode,0,x.stderr)
        self.assertAlmostEqual(json.loads(x.stdout)["result"],(256+84)*(154.4+84))
        self.assertEqual(self.cli("math","unknown","42").returncode,2)
        self.assertEqual(self.cli("math","focus_pop","nan").returncode,2)
        self.assertEqual(self.cli("math","rgba_bytes","5").returncode,2)
    def test_blob_diff_pinned_git_fixtures(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            for d in (a,b):
                subprocess.run(["git","init","-q",d],check=True)
                subprocess.run(["git","-C",d,"config","user.email","example@example.test"],check=True)
                subprocess.run(["git","-C",d,"config","user.name","Synthetic"],check=True)
                Path(d,"x").write_text("same")
                subprocess.run(["git","-C",d,"add","x"],check=True)
                subprocess.run(["git","-C",d,"commit","-qm","synthetic"],check=True)
            aa=mod.tree_blobs(Path(a),"HEAD");bb=mod.tree_blobs(Path(b),"HEAD")
            self.assertEqual(aa,bb)
    def test_external_missing_and_moving_ref_rejected(self):
        self.assertEqual(self.cli("forensics","--external-repo","/does-not-exist","--external-rev","0"*40).returncode,2)
    def test_test_command_does_not_claim_native(self):
        x=self.cli("test");self.assertEqual(x.returncode,0,x.stderr)
        self.assertEqual(json.loads(x.stdout)["native"],"NOT_RUN")
if __name__=="__main__":unittest.main()
