import unittest
import os
import sys

# Ensure backend path is available
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(backend_dir)
for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.services.cohort_service import cohort_service
from backend.app.api.v1.devices import get_device_comparison


class TestDeviceAnalyticsAndCRO(unittest.TestCase):

    def test_device_comparison_schema_and_metrics(self):
        res = get_device_comparison()
        self.assertIsNotNone(res)
        self.assertIn("iOS converts", res.summary_insight)
        self.assertEqual(len(res.devices), 2)

        ios_device = next(d for d in res.devices if d.os == "iOS")
        android_device = next(d for d in res.devices if d.os == "Android")

        # Verify positive volume
        self.assertGreater(ios_device.leads, 0)
        self.assertGreater(android_device.leads, 0)

        # Verify shares sum to ~100%
        total_share = ios_device.leads_share_pct + android_device.leads_share_pct
        self.assertAlmostEqual(total_share, 100.0, delta=1.0)

        # Verify booking parity (~60%)
        self.assertAlmostEqual(ios_device.booked_pct, 60.0, delta=10.0)
        self.assertAlmostEqual(android_device.booked_pct, 60.0, delta=10.0)

        # Verify attendance gap (iOS attendance higher than Android)
        self.assertGreater(ios_device.attended_pct, android_device.attended_pct)
        self.assertGreaterEqual(ios_device.conversion_ratio_vs_android, 1.5)

    def test_cro_leak_detection_recommendation(self):
        res = cohort_service.get_device_comparison()
        self.assertIn("Attendance", res.summary_insight)
        self.assertIn("reminder", res.summary_insight.lower())


if __name__ == "__main__":
    unittest.main()
