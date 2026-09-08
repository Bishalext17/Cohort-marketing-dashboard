-- ============================================================
-- 19 · WHY IT IS SLOW, AND THE CHEAP FIXES FIRST
--
-- Five things in the current query are expensive. Ranked by likely cost.
-- Try SECTION A (indexes) BEFORE the rewrite — it may be enough on its own and
-- takes two minutes.
-- ============================================================
--
-- 1. OR INSIDE A JOIN CONDITION (both demo CTEs)
--       ON ( csb.leads_contact_utm_id = cl.lead_key
--         OR ( csb.parent_id = p.id AND ... ) )
--    MySQL cannot use an index for an OR across two different columns. It falls
--    back to scanning classschedulebookings for every cohort lead. With ~4,500
--    leads and a large bookings table this alone can dominate the runtime.
--
-- 2. CORRELATED NOT EXISTS AGAINST A CTE (both demo CTEs)
--       NOT EXISTS (SELECT 1 FROM cohort_leads c2 WHERE c2.lead_key = ...)
--    cohort_leads is materialised WITHOUT an index, so each probe is a scan of
--    the materialised result. Runs once per candidate booking row.
--
-- 3. UNBOUNDED `prior` SUBQUERY (Converted)
--       SELECT parent_id, MIN(DATE(created_at)) FROM invoices
--       WHERE invoice_type='regular' GROUP BY 1
--    No date bound and no parent bound — this aggregates the ENTIRE invoices
--    table on every single run, then throws away all but a few thousand rows.
--
-- 4. CORRELATED EXISTS PER INVOICE (conversions_after_demo)
--    Joins three tables for every invoice row in scope.
--
-- 5. NO DATE FLOOR ON classschedulebookings
--    The only bound is the per-row BETWEEN against each lead's window, which
--    cannot be pushed down into an index seek. The whole bookings table is a
--    candidate for every lead.
--
-- Also: DATE(csb.created_at) wraps the column, so even a good index on
-- created_at cannot be used for the range. Compare on the raw column instead.


-- ============================================================
-- SECTION A · INDEXES — DO THIS FIRST
-- Two minutes, no query changes, may fix it outright.
-- ============================================================

-- the new FK column, used by the deterministic join
ALTER TABLE classschedulebookings ADD INDEX idx_lcui (leads_contact_utm_id);

-- the fallback join + date range
ALTER TABLE classschedulebookings ADD INDEX idx_parent_created (parent_id, created_at);
ALTER TABLE classschedulebookings ADD INDEX idx_demo_created (demo_class, deleted_at, created_at);

-- the lead -> parent bridge
ALTER TABLE parents ADD INDEX idx_mobile (mobile_number, deleted_at);

-- the prior-payment lookup and the Converted join
ALTER TABLE invoices ADD INDEX idx_parent_type_created (parent_id, invoice_type, created_at);

-- the event log (from the original review; check before re-adding)
ALTER TABLE leads_contact_event_logs
  ADD INDEX idx_evt_created (event_type, deleted_at, created_at),
  ADD INDEX idx_phone (phone);

-- class date range
ALTER TABLE classschedules ADD INDEX idx_class_date (class_date, deleted_at);

-- facebook ads capture date
ALTER TABLE facebookads ADD INDEX idx_capture (capture_date);


-- Check what already exists before adding duplicates:
SELECT table_name, index_name, GROUP_CONCAT(column_name ORDER BY seq_in_index) AS cols
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name IN ('classschedulebookings','parents','invoices',
                     'leads_contact_event_logs','classschedules','facebookads')
GROUP BY 1,2 ORDER BY 1,2;


-- ============================================================
-- SECTION B · MEASURE BEFORE AND AFTER
-- Run EXPLAIN ANALYZE on the master query (MySQL 8.0.18+). Look for:
--   · "Table scan on classschedulebookings" with a large rows= estimate
--   · "Nested loop" with actual loops in the thousands
--   · any node whose actual time dwarfs the rest
-- ============================================================
/*
EXPLAIN ANALYZE
<paste the master query with literal dates instead of {{variables}}>;
*/


-- ============================================================
-- SECTION C · SIZE THE TABLES
-- Tells you whether this is a data-volume problem or a plan problem.
-- ============================================================
SELECT table_name, table_rows, ROUND(data_length/1024/1024) AS data_mb,
       ROUND(index_length/1024/1024) AS index_mb
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN ('classschedulebookings','classschedules','classes','parents',
                     'invoices','leads_contact_event_logs','facebookads')
ORDER BY table_rows DESC;
