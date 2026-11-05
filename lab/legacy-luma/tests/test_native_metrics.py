import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from native_metrics import nearest_rank, frame_budgets, rgba_bytes, calculations

class MetricTests(unittest.TestCase):
    def test_hand_computed_nearest_ranks(self):
        values = [17, 16, 50, 16]
        self.assertEqual([nearest_rank(values, p) for p in (50,90,95,99)], [16,50,50,50])
        self.assertIsNone(nearest_rank([], 95))

    def test_invalid_samples_are_not_silently_dropped(self):
        for values in ([float("nan")], [float("inf")]):
            with self.assertRaises(ValueError): nearest_rank(values, 95)
        for p in (0, -1, 101, float("nan")):
            with self.assertRaises(ValueError): nearest_rank([1], p)

    def test_refresh_dependent_budgets(self):
        values = {r["refresh_hz"]: r["period_ms"] for r in frame_budgets()}
        self.assertEqual(values[50], 20)
        self.assertAlmostEqual(values[60], 16.6666666667)
        self.assertAlmostEqual(values[120], 8.3333333333)

    def test_rgba_payload_is_not_gpu_measurement(self):
        self.assertEqual(rgba_bytes(1920,1080,2), 16_588_800)
        self.assertEqual(rgba_bytes(3840,2160,2), 66_355_200)
        self.assertTrue(calculations()["not_measurements"])
        with self.assertRaises(ValueError): rgba_bytes(0,1080)

    def test_focus_depth_keeps_face_geometry(self):
        c = calculations()["home_card"]
        self.assertEqual(c["face"], [256,154.4])
        self.assertAlmostEqual(c["gap"], 25.6)
        self.assertGreater(c["candidate_shadow_area_ratio"], 1)
        self.assertLess(c["candidate_shadow_area_ratio"], 1.3)

if __name__ == "__main__":
    unittest.main()
