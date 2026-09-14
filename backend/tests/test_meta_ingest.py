import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)
for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.scripts.ingest_meta_direct import MetaDirectIngestionEngine

class TestMetaDirectIngest(unittest.TestCase):
    def setUp(self):
        self.engine = MetaDirectIngestionEngine(
            access_token="test_token_xyz",
            account_ids=["123456789"],
            batch_size=10,
            inter_batch_delay=0.0,
            dry_run=True
        )

    def test_transform_record_with_nested_actions(self):
        """Test transformation correctly unnests actions and casts numeric fields."""
        raw_meta_row = {
            "date_start": "2026-09-12",
            "account_id": "123456789",
            "campaign_id": "camp_001",
            "campaign_name": "India_Phonics_TOF",
            "adset_id": "adset_001",
            "adset_name": "Parents_30_45",
            "ad_id": "ad_001",
            "ad_name": "Creative_V1_Video",
            "impression_device": "iphone",
            "publisher_platform": "facebook",
            "spend": "1450.75",
            "impressions": "12450",
            "clicks": "320",
            "inline_link_clicks": "285",
            "actions": [
                {"action_type": "complete_registration", "value": "18"},
                {"action_type": "start_trial", "value": "12"},
                {"action_type": "purchase", "value": "3"},
                {"action_type": "landing_page_view", "value": "240"}
            ]
        }

        res = self.engine.transform_record(raw_meta_row)

        self.assertEqual(res["date"], "2026-09-12")
        self.assertEqual(res["account_id"], "123456789")
        self.assertEqual(res["spend"], 1450.75)
        self.assertEqual(res["impressions"], 12450)
        self.assertEqual(res["clicks"], 320)
        self.assertEqual(res["link_clicks"], 285)
        self.assertEqual(res["landing_page_views"], 240)
        self.assertEqual(res["complete_registration"], 18)
        self.assertEqual(res["start_trial"], 12)
        self.assertEqual(res["purchases"], 3)
        self.assertEqual(res["impression_device"], "iphone")

    def test_transform_record_missing_and_malformed_fields(self):
        """Test graceful degradation when Meta API returns empty/null values."""
        raw_row = {
            "date_start": "2026-09-12",
            "spend": None,
            "impressions": "invalid_number",
            "actions": None
        }

        res = self.engine.transform_record(raw_row)

        self.assertEqual(res["spend"], 0.0)
        self.assertEqual(res["impressions"], 0)
        self.assertEqual(res["clicks"], 0)
        self.assertEqual(res["complete_registration"], 0)
        self.assertEqual(res["campaign_name"], "Unmapped")

    def test_dry_run_batch_upsert_skips_db(self):
        """Test dry-run mode processes memory pipeline without touching DB."""
        sample_records = [
            {"date": f"2026-09-0{i}", "account_id": "123", "spend": 100.0}
            for i in range(1, 25)
        ]

        upserted_count = self.engine.batch_upsert(sample_records)
        self.assertEqual(upserted_count, 24)

    @patch("requests.get")
    def test_fetch_insights_pagination_mock(self, mock_get):
        """Test cursor-based multi-page extraction."""
        # Page 1 response
        mock_resp_p1 = MagicMock()
        mock_resp_p1.status_code = 200
        mock_resp_p1.json.return_value = {
            "data": [{"ad_id": "ad_1", "spend": "50"}],
            "paging": {"next": "https://graph.facebook.com/v20.0/next_cursor"}
        }

        # Page 2 response
        mock_resp_p2 = MagicMock()
        mock_resp_p2.status_code = 200
        mock_resp_p2.json.return_value = {
            "data": [{"ad_id": "ad_2", "spend": "75"}],
            "paging": {}
        }

        mock_get.side_effect = [mock_resp_p1, mock_resp_p2]

        records = self.engine.fetch_insights_for_account(
            account_id="123456789",
            date_from="2026-09-01",
            date_to="2026-09-02"
        )

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["ad_id"], "ad_1")
        self.assertEqual(records[1]["ad_id"], "ad_2")


if __name__ == "__main__":
    unittest.main()
