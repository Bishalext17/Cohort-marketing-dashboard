import unittest
import os
import sys
from datetime import datetime, timedelta

# Ensure backend and root paths are available
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(backend_dir)
for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.main import health_check
from backend.app.api.v1.metadata import get_filter_metadata
from backend.app.api.v1.kpis import get_kpi_tiles
from backend.app.api.v1.cohorts import get_master_cohort_table, get_cohort_maturity
from backend.app.api.v1.devices import get_device_comparison
from backend.app.api.v1.followups import get_followup_contacts, export_followup_csv, update_lead_status
from backend.app.api.v1.query_runner import list_queries, get_query_template, run_query
from backend.app.models.schemas import FilterParams, UpdateLeadStatusRequest, QueryRunRequest
from backend.app.services.cohort_service import cohort_service
from backend.app.services.sql_engine import sql_engine

class TestCohortDashboard(unittest.TestCase):

    def test_health_endpoint(self):
        data = health_check()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("version", data)
        self.assertIn("engine_mode", data)

    def test_metadata_endpoint(self):
        data = get_filter_metadata()
        self.assertIn("channels", data)
        self.assertIn("countries", data)
        self.assertIn("platforms", data)
        self.assertIn("courses", data)
        self.assertIn("cohort_options", data)
        self.assertIn("Till date", data["cohort_options"])
        self.assertIn("D0", data["cohort_options"])

    def test_kpi_calculations_and_totals_integrity(self):
        filters = FilterParams(
            cohort_period="Till date",
            date_from="2026-07-01",
            date_to="2026-07-31",
            slicers=["date"]
        )
        
        master = get_master_cohort_table(filters)
        self.assertGreater(master.row_count, 0)
        tot = master.totals
        
        # Check sum of components matches total
        sum_spend = sum(r.spend for r in master.rows)
        sum_contacts = sum(r.contacts_registered for r in master.rows)
        sum_conversions = sum(r.conversions for r in master.rows)
        sum_revenue = sum(r.new_revenue for r in master.rows)
        
        self.assertAlmostEqual(tot.spend, sum_spend, delta=20.0)
        self.assertEqual(tot.contacts_registered, sum_contacts)
        self.assertEqual(tot.conversions, sum_conversions)
        self.assertAlmostEqual(tot.new_revenue, sum_revenue, delta=20.0)
        
        # Check recalculated ratios (Never average ratios)
        expected_cpl = round((tot.spend / tot.contacts_registered), 2) if tot.contacts_registered > 0 else 0.0
        expected_arpu = round((tot.new_revenue / tot.conversions), 2) if tot.conversions > 0 else 0.0
        expected_roas = round((tot.new_revenue / tot.spend), 2) if tot.spend > 0 else 0.0
        
        self.assertEqual(tot.cpl, expected_cpl)
        self.assertEqual(tot.arpu, expected_arpu)
        self.assertEqual(tot.roas, expected_roas)

        # Check KPI tiles match Master Totals
        kpis = get_kpi_tiles(filters)
        self.assertEqual(kpis.spend.numeric_value, tot.spend)
        self.assertEqual(kpis.leads.numeric_value, float(tot.contacts_registered))
        self.assertEqual(kpis.cpl.numeric_value, tot.cpl)
        self.assertEqual(kpis.conversions.numeric_value, float(tot.conversions))
        self.assertEqual(kpis.revenue.numeric_value, tot.new_revenue)

    def test_maturity_gating(self):
        end_d = datetime.now().strftime("%Y-%m-%d")
        start_d = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        filters = FilterParams(date_from=start_d, date_to=end_d)
        
        # Till date: 0 dropped dates
        filters.cohort_period = "Till date"
        till_date_maturity = get_cohort_maturity(filters)
        self.assertEqual(till_date_maturity.dropped_dates, 0)
        self.assertEqual(till_date_maturity.counted_dates, till_date_maturity.total_dates)
        
        # D3: 3 dropped dates
        filters.cohort_period = "D3"
        d3_maturity = get_cohort_maturity(filters)
        self.assertEqual(d3_maturity.dropped_dates, 3)
        self.assertEqual(d3_maturity.counted_dates, d3_maturity.total_dates - 3)
        
        # D7: 7 dropped dates
        filters.cohort_period = "D7"
        d7_maturity = get_cohort_maturity(filters)
        self.assertEqual(d7_maturity.dropped_dates, 7)
        self.assertEqual(d7_maturity.counted_dates, d7_maturity.total_dates - 7)

    def test_device_diagnostics_endpoint(self):
        data = get_device_comparison()
        self.assertIn("devices", data.model_dump())
        self.assertGreaterEqual(len(data.devices), 2)
        ios_data = next((d for d in data.devices if d.os == "iOS"), None)
        android_data = next((d for d in data.devices if d.os == "Android"), None)
        self.assertIsNotNone(ios_data)
        self.assertIsNotNone(android_data)
        self.assertGreater(ios_data.conversion_ratio_vs_android, 1.0)

    def test_followup_contacts_and_status_update(self):
        # 1. Get contacts
        data = get_followup_contacts("all")
        self.assertGreater(len(data.contacts), 0)
        lead = data.contacts[0]
        
        # 2. Update status and notes
        updated = update_lead_status(
            lead_id=lead.lead_id,
            req=UpdateLeadStatusRequest(
                status="Follow-up Call Scheduled",
                followup_priority="High",
                notes="Parent requested evening callback for Bhagavad Gita course."
            )
        )
        self.assertEqual(updated.status, "Follow-up Call Scheduled")
        self.assertEqual(updated.followup_priority, "High")
        self.assertEqual(updated.notes, "Parent requested evening callback for Bhagavad Gita course.")
        
        # 3. CSV Export includes updated notes
        csv_res = export_followup_csv("all")
        self.assertEqual(csv_res.status_code, 200)
        csv_body = csv_res.body.decode("utf-8")
        self.assertIn("Parent requested evening callback", csv_body)

    def test_sql_engine_template_compiler(self):
        template = "SELECT * FROM leads WHERE created_at >= {{from_date}} [[AND campaign IN ({{campaign_nm}})]] [[AND country = {{country_cd}}]];"
        
        # Case 1: All params provided
        compiled_1 = sql_engine.compile_template(template, {
            "from_date": "2026-07-01",
            "campaign_nm": ["Camp_A", "Camp_B"],
            "country_cd": "IN"
        })
        self.assertIn("created_at >= '2026-07-01'", compiled_1)
        self.assertIn("AND campaign IN ('Camp_A', 'Camp_B')", compiled_1)
        self.assertIn("AND country = 'IN'", compiled_1)
        
        # Case 2: Optional params omitted
        compiled_2 = sql_engine.compile_template(template, {
            "from_date": "2026-07-01",
            "campaign_nm": None,
            "country_cd": None
        })
        self.assertIn("created_at >= '2026-07-01'", compiled_2)
        self.assertNotIn("AND campaign IN", compiled_2)
        self.assertNotIn("AND country =", compiled_2)

    def test_query_runner_api(self):
        queries = list_queries()
        self.assertGreater(len(queries), 0)
        
        first_q = queries[0]
        rel_path = first_q["relative_path"] if isinstance(first_q, dict) else first_q.relative_path
        tpl = get_query_template(rel_path)
        self.assertIn("sql", tpl)
        
        # Run query in simulation mode
        run_res = run_query(QueryRunRequest(
            query_path=rel_path,
            cohort_days=9999,
            from_date="2026-07-01",
            to_date="2026-07-31"
        ))
        self.assertIsNotNone(run_res.compiled_sql)
        self.assertGreaterEqual(run_res.duration_ms, 0)

    def test_cache_manager_operations(self):
        from backend.app.services.cache_manager import cache_manager
        
        # 1. Set and Get
        cache_manager.set("test:key1", {"metric": 100}, ttl=60)
        cached = cache_manager.get("test:key1")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["metric"], 100)
        
        # 2. Invalidation
        cache_manager.invalidate_prefix("test:")
        self.assertIsNone(cache_manager.get("test:key1"))
        
        # 3. Stats
        stats = cache_manager.get_stats()
        self.assertIn("hits", stats)
        self.assertIn("misses", stats)
        self.assertIn("hit_ratio_pct", stats)

if __name__ == "__main__":
    unittest.main()
