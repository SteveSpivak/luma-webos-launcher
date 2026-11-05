import unittest

from research.scripts.analyze_native_diagnostics import analyze, nearest_rank


class DiagnosticsAnalysis(unittest.TestCase):
    def test_nearest_rank_p99_matches_hand_computed_order_statistics(self):
        samples = list(range(1, 101))
        self.assertEqual(nearest_rank(samples, 50), 50)
        self.assertEqual(nearest_rank(samples, 95), 95)
        self.assertEqual(nearest_rank(samples, 99), 99)
        self.assertEqual(nearest_rank([7], 99), 7)

    def test_invalid_intervals_and_percentiles_refused(self):
        for samples in ([], [0], [-1], [float("nan")], [float("inf")], ["16"]):
            with self.assertRaises(ValueError):
                nearest_rank(samples, 99)
        with self.assertRaises(ValueError):
            nearest_rank([16], 0)

    def test_missing_profile_is_unknown_not_zero(self):
        result = analyze({})
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIsNone(result["p99_ms"])
        self.assertIsNone(result["gpu_memory_bytes"])

    def test_spike_association_is_not_causal_or_gpu_evidence(self):
        frames = [{"interval_ms": 16, "image_ms": 0}, {"interval_ms": 80, "image_ms": 60, "swap_ms": 5}]
        result = analyze({"profile": {"timeline": frames, "pacing": {"p99_ms": 80}}}, "SYNTHETIC")
        self.assertEqual(result["p99_ms"], 80)
        self.assertTrue(result["native_p99_matches"])
        self.assertEqual(result["top_interval_associations"][0]["image_ms"], 60)
        self.assertEqual(result["attribution"], "ASSOCIATION_NOT_CAUSATION")
        self.assertIsNone(result["gpu_time_ms"])
        self.assertEqual(result["focus_latency"]["status"], "UNKNOWN")

    def test_future_focus_trace_summary_is_explicitly_call_latency(self):
        result = analyze({"profile": {"timeline": [{"interval_ms": 16}]}, "focus_latency_ms": [10, 20, 30]}, "SYNTHETIC")
        self.assertEqual(result["focus_latency"]["p99_ms"], 30)
        self.assertIn("not photons", result["focus_latency"]["meaning"])


if __name__ == "__main__":
    unittest.main()
