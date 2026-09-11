import os
import sys
import unittest
import shutil

# Ensure path includes root
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)
for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.app.core.audit_logger import AuditLogger, AuditCategory, AuditLevel
from backend.app.services.sql_engine import sql_engine
from backend.app.services.cohort_service import cohort_service
from backend.app.models.schemas import FilterParams

class TestAuditLogger(unittest.TestCase):
    def setUp(self):
        self.test_log_dir = os.path.join(current_dir, f"test_logs_{os.getpid()}")
        if os.path.exists(self.test_log_dir):
            shutil.rmtree(self.test_log_dir, ignore_errors=True)
        self.logger = AuditLogger(log_dir=self.test_log_dir, max_memory_entries=10)

    def tearDown(self):
        if hasattr(self, 'logger'):
            self.logger.close()
        if os.path.exists(self.test_log_dir):
            shutil.rmtree(self.test_log_dir, ignore_errors=True)

    def test_log_event_and_memory_buffer(self):
        """Test logging an event records properly to file and memory."""
        ev = self.logger.log_event(
            category=AuditCategory.QUERY_EXECUTION,
            action="TEST_QUERY",
            details={"param_a": 123},
            duration_ms=45.6
        )
        self.assertEqual(ev["action"], "TEST_QUERY")
        self.assertEqual(ev["category"], "QUERY_EXECUTION")
        self.assertEqual(ev["duration_ms"], 45.6)

        # Verify in-memory buffer
        logs = self.logger.get_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["action"], "TEST_QUERY")

        # Verify disk file creation
        self.assertTrue(os.path.exists(self.logger.log_file))

    def test_zero_memory_leak_bounded_deque(self):
        """Test that memory buffer never exceeds max_memory_entries (O(1) pop)."""
        # Capacity is 10 for test
        for i in range(50):
            self.logger.log_event(
                category=AuditCategory.LEAD_MUTATION,
                action=f"MUTATION_{i}",
                details={"index": i}
            )

        logs = self.logger.get_logs(limit=100)
        # Should be strictly capped at 10 in RAM
        self.assertEqual(len(logs), 10)
        # Most recent first
        self.assertEqual(logs[0]["action"], "MUTATION_49")
        self.assertEqual(logs[-1]["action"], "MUTATION_40")

    def test_log_filtering_and_search(self):
        """Test filtering by category, level, and keyword search."""
        self.logger.log_event(
            category=AuditCategory.QUERY_EXECUTION,
            action="METRICS_CALC",
            details={"cohort_days": "D1"},
            level=AuditLevel.INFO
        )
        self.logger.log_event(
            category=AuditCategory.SYSTEM_ERROR,
            action="SYNTAX_ERROR",
            details={"error_code": 1064},
            level=AuditLevel.ERROR
        )

        # Filter by category
        err_logs = self.logger.get_logs(category="SYSTEM_ERROR")
        self.assertEqual(len(err_logs), 1)
        self.assertEqual(err_logs[0]["action"], "SYNTAX_ERROR")

        # Search keyword
        search_res = self.logger.get_search = self.logger.get_logs(search="cohort_days")
        self.assertEqual(len(search_res), 1)
        self.assertEqual(search_res[0]["action"], "METRICS_CALC")

    def test_flush_memory(self):
        """Test manual flushing resets RAM buffer."""
        self.logger.log_event(
            category=AuditCategory.CACHE_INVALIDATION,
            action="CACHE_PURGE",
            details={"keys": 15}
        )
        self.assertEqual(len(self.logger.get_logs()), 1)

        cleared = self.logger.flush_memory()
        self.assertEqual(cleared, 1)
        self.assertEqual(len(self.logger.get_logs()), 0)

    def test_sql_engine_audit_integration(self):
        """Test SQLEngine execution triggers audit events."""
        from backend.app.core.audit_logger import audit_logger
        initial_count = len(audit_logger.get_logs(category="QUERY_EXECUTION"))

        template = "SELECT {{cohort_days}} AS val;"
        params = {"cohort_days": "1"}
        sql_engine.execute_query(template, params, force_refresh=True)

        after_count = len(audit_logger.get_logs(category="QUERY_EXECUTION"))
        self.assertGreater(after_count, initial_count)

if __name__ == "__main__":
    unittest.main()
