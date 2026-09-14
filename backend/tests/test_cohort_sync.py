import os
import sys
import unittest

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)
for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.scripts.sync_cohort_cache import CohortCacheSyncEngine

class TestCohortCacheSync(unittest.TestCase):
    def setUp(self):
        self.engine = CohortCacheSyncEngine(
            rolling_days=35,
            inter_chunk_delay=0.0,
            dry_run=True
        )

    def test_date_chunking_strategy(self):
        """Test wide date ranges are cleanly chunked into monthly batches."""
        chunks = self.engine.get_date_chunks(
            start_date="2026-01-01",
            end_date="2026-04-01",
            chunk_days=30
        )
        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(chunks[0][0], "2026-01-01")
        self.assertEqual(chunks[-1][1], "2026-04-01")

    def test_dry_run_sync_execution(self):
        """Test dry run handles full date window cleanly."""
        res = self.engine.run_sync(
            mode="incremental",
            custom_from="2026-08-01",
            custom_to="2026-09-01"
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertGreater(res["rows_processed"], 0)


if __name__ == "__main__":
    unittest.main()
