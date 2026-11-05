from __future__ import annotations
import copy, json, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from nuvio_launch_contract import build_launch
from mock_webos_nuvio import MockApplicationManager
from cw_fixture import validate_feed, ProfileCache
from advanced_diagnostics import analyze
ROOT=Path(__file__).resolve().parents[1]
def feed():return json.loads((ROOT/"fixtures/cw-valid.json").read_text())
def summary():return json.loads((ROOT/"fixtures/advanced-summary.json").read_text())
class LaunchHarness(unittest.TestCase):
    def test_valid_launch_and_no_autoplay(self):
        w=MockApplicationManager(); r=w.call("luna://com.webos.applicationManager/launch",build_launch("movie","tmdb","603"))
        self.assertEqual(r["returnValue"],True)
        self.assertEqual(w.nuvio.route,"detail")
        self.assertEqual(w.nuvio.opened,1)
        self.assertFalse(w.nuvio.playing)
        self.assertEqual(w.nuvio.back(),"home")
    def test_missing_app_failed(self):
        w=MockApplicationManager();w.nuvio.installed=False
        self.assertFalse(w.call("luna://com.webos.applicationManager/launch",build_launch("movie","tmdb","603"))["returnValue"])
        self.assertEqual(w.nuvio.opened,0)
    def test_deferred_profile_and_relaunch(self):
        w=MockApplicationManager(); w.nuvio.switch_profile()
        w.call("luna://com.webos.applicationManager/launch",build_launch("movie","tmdb","603"))
        w.call("luna://com.webos.applicationManager/launch",build_launch("series","imdb","tt0903747"))
        self.assertEqual(w.nuvio.opened,0)
        self.assertTrue(w.nuvio.ready("demo"))
        self.assertEqual(w.nuvio.current_title,"nuvio://imdb/series/tt0903747")
        self.assertFalse(w.nuvio.ready("demo"))
        self.assertEqual(w.nuvio.opened,1)
    def test_duplicate_title_no_duplicate_detail(self):
        w=MockApplicationManager();p=build_launch("movie","tmdb","603")
        w.call("luna://com.webos.applicationManager/launch",p)
        w.call("luna://com.webos.applicationManager/launch",p)
        self.assertEqual(w.nuvio.opened,1)
    def test_wrong_service_and_malicious_payload(self):
        w=MockApplicationManager()
        with self.assertRaises(ValueError): w.call("luna://com.webos.service.applicationmanager/closeByAppId",build_launch("movie","tmdb","603"))
        with self.assertRaises(ValueError): w.call("luna://com.webos.applicationManager/launch",{"id":"com.webos.app.home","params":{}})
        self.assertEqual(w.nuvio.opened,0)
    def test_profile_switch_clears_pending(self):
        w=MockApplicationManager(); w.nuvio.switch_profile()
        w.call("luna://com.webos.applicationManager/launch",build_launch("movie","tmdb","603"))
        w.nuvio.switch_profile()
        self.assertFalse(w.nuvio.ready("other"))
        self.assertIsNone(w.nuvio.current_title)

class ContinueWatching(unittest.TestCase):
    def test_valid_and_profile_cache(self):
        f=feed(); self.assertEqual(len(validate_feed(f,"demo-profile-a","2026-11-05T12:01:00Z")),2)
        c=ProfileCache();c.switch_profile("demo-profile-a");c.accept(f,"2026-11-05T12:01:00Z")
        self.assertEqual(len(c.items),2); c.switch_profile("demo-profile-b")
        self.assertEqual(c.items,[]);self.assertEqual(c.revision,0)
    def test_fails_profile_mismatch_and_stale(self):
        f=feed()
        with self.assertRaises(ValueError):validate_feed(f,"other","2026-11-05T12:01:00Z")
        with self.assertRaises(ValueError):validate_feed(f,"demo-profile-a","2026-11-05T12:11:00Z")
        with self.assertRaises(ValueError):validate_feed(f,"demo-profile-a","2026-11-05T12:01:00Z",3)
    def test_rejects_url_and_bad_progress(self):
        f=feed();f["items"][0]["artwork_ref"]="https://secret.example/stream"
        with self.assertRaises(ValueError):validate_feed(f,"demo-profile-a","2026-11-05T12:01:00Z")
        f=feed();f["items"][0]["progress_seconds"]=999999
        with self.assertRaises(ValueError):validate_feed(f,"demo-profile-a","2026-11-05T12:01:00Z")
    def test_rejects_excessive_or_duplicate_items(self):
        f=feed(); f["items"]=f["items"]*11
        with self.assertRaises(ValueError):validate_feed(f,"demo-profile-a","2026-11-05T12:01:00Z")
        f=feed();f["items"].append(copy.deepcopy(f["items"][0]))
        with self.assertRaises(ValueError):validate_feed(f,"demo-profile-a","2026-11-05T12:01:00Z")
    def test_rejects_future_and_injected_fields(self):
        f=feed();f["generated_at"]="2026-11-05T12:05:00Z"
        with self.assertRaises(ValueError):validate_feed(f,"demo-profile-a","2026-11-05T12:01:00Z")
        f=feed();f["token"]="must-not-leak"
        with self.assertRaises(ValueError):validate_feed(f,"demo-profile-a","2026-11-05T12:01:00Z")

class Diagnostics(unittest.TestCase):
    def test_valid_aggregate_never_invents_p99(self):
        x=analyze(summary())
        self.assertEqual(x["status"],"ANALYZED")
        self.assertEqual(x["pacing"]["p95_ms"],20)
        self.assertIsNone(x["p99_ms"])
        self.assertIsNone(x["gpu_memory_bytes"])
    def test_rejects_missing_or_bad_samples(self):
        x=summary();del x["warmup_frames"]
        with self.assertRaises(ValueError):analyze(x)
        x=summary();x["pacing"]["p95_ms"]=55
        with self.assertRaises(ValueError):analyze(x)
    def test_no_timeline_is_not_native_measurement(self):
        x=summary();x["pacing"]=None;x["cpu_submission"]=None
        y=analyze(x);self.assertEqual(y["status"],"INSUFFICIENT_SAMPLES")
        self.assertEqual(y["evidence"],"INPUT_ONLY_NOT_REMEASURED")
if __name__=="__main__":unittest.main()
