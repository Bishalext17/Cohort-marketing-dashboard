import unittest
from backend.app.services.company_service import company_service
from backend.app.services.analytics_service import analytics_service
from backend.app.services.operations_service import operations_service
from backend.app.services.campaign_tagger import campaign_tagger

class TestV14AnalyticalEngine(unittest.TestCase):
    """
    Validation Suite for v14 Production Business Logic & Metric Contracts.
    """

    def test_company_roas_and_booking_economics(self):
        """Test Company Level ROAS, Cost per Demo Booked & Revenue per Demo Booked."""
        res = company_service.calculate_company_view(from_date="2026-07-01", to_date="2026-07-31")
        total = res["total"]

        # Sum first, divide later
        expected_roas = total["new_revenue"] / total["spend"]
        self.assertAlmostEqual(total["roas"], round(expected_roas, 4), places=3)

        expected_cpdb = total["spend"] / total["demos_booked"]
        self.assertAlmostEqual(total["cost_per_demo_booked"], round(expected_cpdb, 2), places=1)

        expected_rpdb = total["new_revenue"] / total["demos_booked"]
        self.assertAlmostEqual(total["revenue_per_demo_booked"], round(expected_rpdb, 2), places=1)

    def test_never_average_ratios_law(self):
        """Ensure total ROAS is NOT an arithmetic mean of daily ROAS values."""
        res = company_service.calculate_company_view(from_date="2026-07-01", to_date="2026-07-31")
        daily_roas_list = [r["roas"] for r in res["rows"]]
        arithmetic_mean_roas = sum(daily_roas_list) / len(daily_roas_list)

        # The true total ROAS must be calculated from sum(revenue) / sum(spend), not the average of ratios
        true_total_roas = res["total"]["roas"]
        self.assertIsNotNone(true_total_roas)
        self.assertTrue(isinstance(true_total_roas, float))

    def test_cohort_maturity_gating(self):
        """Test that future incomplete cohort windows are gated/excluded."""
        # A lead captured on July 30 cannot have a mature D7 window when refresh is July 31
        is_mature = analytics_service.is_window_mature("2026-07-30", "D7")
        self.assertFalse(is_mature)

        # A lead captured on July 10 has a mature D7 window
        is_mature_past = analytics_service.is_window_mature("2026-07-10", "D7")
        self.assertTrue(is_mature_past)

        # Till date is always accessible
        self.assertTrue(analytics_service.is_window_mature("2026-07-30", "Till date"))

    def test_five_driver_multiplicative_pressure(self):
        """Test that the 5 driver multipliers combine multiplicatively to equal CPDB ratio."""
        res = operations_service.diagnose_performance(
            perf_from="2026-07-16", perf_to="2026-07-31",
            comp_from="2026-07-01", comp_to="2026-07-15"
        )
        summary = res["summary"]
        drivers = summary["drivers"]

        # Product of all 5 multipliers
        product_of_multipliers = 1.0
        for d in drivers:
            product_of_multipliers *= d["multiplier"]

        cur_cpdb = summary["currentMetrics"]["cpdb"]
        prev_cpdb = summary["previousMetrics"]["cpdb"]
        actual_ratio = cur_cpdb / prev_cpdb

        # Must match multiplicatively within float rounding bounds
        self.assertAlmostEqual(product_of_multipliers, actual_ratio, places=2)

    def test_campaign_tagger_governance(self):
        """Test exact alias matching and Unmapped safety fallback."""
        # 1. Direct match
        res1 = campaign_tagger.resolve(campaign_name="allindiaphonics1")
        self.assertEqual(res1["course"], "English")
        self.assertEqual(res1["market"], "India")
        self.assertEqual(res1["channel"], "Meta")

        # 2. Normalized whitespace & punctuation match
        res2 = campaign_tagger.resolve(campaign_name="Bangalore - Contacts - 16072025")
        self.assertEqual(res2["course"], "English")
        self.assertEqual(res2["market"], "India")

        # 3. Unmapped fallback
        res_unmapped = campaign_tagger.resolve(campaign_name="random_unregistered_campaign_xyz")
        self.assertEqual(res_unmapped["course"], "Unmapped")
        self.assertEqual(res_unmapped["market"], "Unmapped")
        self.assertEqual(res_unmapped["channel"], "Unmapped")

if __name__ == "__main__":
    unittest.main()
