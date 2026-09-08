-- ============================================================
-- 25 · WHY THE DASHBOARD IS STILL SLOW
--
-- Query time went 52s -> 15.5s after the rewrite, so that worked. But the
-- dashboard is still slow, and for a different reason.
--
-- THE ARITHMETIC NOBODY DOES
--   Overview has 8 tiles + the master table = 9 cards.
--   Every one runs the FULL 17-CTE pipeline independently.
--   9 x ~15s = over two minutes of database work to render one screen,
--   and 8 of those 9 queries compute exactly the same thing and return one row.
--
-- So there are two problems:
--   A. each card is slower than it needs to be   (fix in SECTION 2 and 3)
--   B. the same work is done 9 times over        (fix in SECTION 1 — biggest win)
-- ============================================================


-- ============================================================
-- SECTION 1 · CACHING — DO THIS FIRST, IT IS THE BIGGEST WIN
--
-- The underlying data refreshes at most a few times a day: Facebook spend lands
-- on a lag, enquiries trickle in. Re-running identical queries on every page
-- load is pure waste.
--
-- Metabase: Admin > Performance (or Settings > Caching)
--   · Turn on caching
--   · Minimum query duration: 10 seconds
--     -> anything slower than 10s gets cached; fast cards stay live
--   · Cache TTL: 2 hours is a reasonable start
--
-- Then per dashboard: ... menu > Edit > Caching > set the same policy.
--
-- EFFECT: the first viewer after each refresh waits. Everyone else gets an
-- instant dashboard. For a report read many times a day and updated a few times
-- a day, this is the single highest-value change available.
--
-- Caveat worth knowing: a cached card will not reflect data that arrived in the
-- last 2 hours. For this dashboard that is fine — the spend it depends on is
-- already a day behind. Do not cache if someone needs same-hour numbers.
-- ============================================================


-- ============================================================
-- SECTION 2 · THE POOLS SCAN FAR MORE THAN THEY NEED TO
--
-- Current bound in book_pool / sched_pool / attended_pool:
--     csb.created_at <  DATE_ADD(CURDATE(), INTERVAL 1 DAY)
--
-- That scans from from_date all the way to TODAY. But nothing after
-- to_date + cohort_days can ever fall inside any lead's window.
--
-- With from_date = to_date = 7 Aug, cohort_days = 0, today = 17 Aug:
--     needed: bookings on 7 Aug          = 1 day
--     scanned: 7 Aug to 17 Aug           = 11 days
--   -> roughly 11x more rows than required, on the largest table in the query.
--
-- FIX: cap the upper bound. Replace the line in book_pool with:
/*
      AND csb.created_at < DATE_ADD(
              LEAST(CURDATE(),
                    CASE WHEN {{cohort_days}} >= 9999 THEN CURDATE()
                         ELSE DATE_ADD({{to_date}}, INTERVAL {{cohort_days}} DAY) END),
              INTERVAL 1 DAY)
*/
-- Same change in sched_pool, but on cs.class_date:
/*
      AND cs.class_date < DATE_ADD(
              LEAST(CURDATE(),
                    CASE WHEN {{cohort_days}} >= 9999 THEN CURDATE()
                         ELSE DATE_ADD({{to_date}}, INTERVAL {{cohort_days}} DAY) END),
              INTERVAL 1 DAY)
*/
-- And in attended_pool, add the same upper bound on cs.class_date.
--
-- NOTE: demos_booked_held compares class_date to CURDATE(), so it still works —
-- that comparison happens on rows already inside the pool.
--
-- EFFECT: large for short windows (D0, D1, D3), none for Till date. Since the
-- dashboard default should be D3, this matters.
-- ============================================================


-- ============================================================
-- SECTION 3 · CONFIRM THE INDEXES ACTUALLY EXIST
-- The rewrite assumed them. If they were never applied, or applied to the wrong
-- columns, the query has no fast path regardless of its shape.
-- ============================================================
SELECT table_name, index_name,
       GROUP_CONCAT(column_name ORDER BY seq_in_index) AS columns
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name IN ('classschedulebookings','classschedules','classes',
                     'parents','invoices','leads_contact_event_logs','facebookads')
GROUP BY 1,2
ORDER BY 1,2;


-- ============================================================
-- SECTION 4 · FIND THE ACTUAL BOTTLENECK
-- Do not guess. This shows which step costs the time.
-- ============================================================
/*
EXPLAIN ANALYZE
<paste 24_kpi_unified.sql, replacing {{variables}} with literal values>;
*/


-- ============================================================
-- SECTION 5 · STRUCTURAL OPTIONS, IF THE ABOVE IS NOT ENOUGH
--
-- 5a. FEWER CARDS ON THE OVERVIEW TAB.
-- 5b. NIGHTLY SUMMARY TABLE. The real fix at scale. (See file 28_nightly_cache.sql)
-- 5c. SPLIT THE DASHBOARD. Overview loads first; heavy detail tabs load lazily.
-- ============================================================


-- ============================================================
-- ORDER I WOULD DO THEM IN
--   1. Turn on caching                    minutes    biggest single win
--   2. Verify indexes exist               minutes    may already be done
--   3. Cap the pool upper bound           minutes    large at D0-D3
--   4. Move the master table off Overview minutes    faster first paint
--   5. EXPLAIN ANALYZE                    an hour    only if still slow
--   6. Nightly summary table              a day      the permanent answer
-- ============================================================
