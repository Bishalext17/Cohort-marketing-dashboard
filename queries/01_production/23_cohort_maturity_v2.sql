-- COHORT MATURITY — rewritten 13 Aug
--
-- WHAT WAS WRONG WITH THE OLD VERSION
--   1. It listed EVERY capture date in the event log, then labelled six of the
--      seven "Outside selected range". Those rows are noise — the reader already
--      knows what range they picked. As history grows this card grows with it.
--   2. leads_on_date counted distinct phones PER DAY. The master de-duplicates
--      by phone across the WHOLE range, so a person who enquired on the 7th and
--      the 8th counts once in the master but twice here. The two cards could
--      never be reconciled.
--   3. It showed no totals, so it could not answer the question it exists for:
--      "how many of my leads did the cohort gate exclude?"
--
-- WHAT THIS VERSION DOES
--   · Only dates inside the selected range.
--   · Same de-duplication as the master, so Counted leads SUM to the master's
--     contacts_registered exactly.
--   · Shows how many days until a dropped date becomes countable.
--
-- Variables: cohort_days (Number), from_date, to_date (Date)
-- ============================================================

WITH deduped AS (
    SELECT
        DATE(e.created_at) AS capture_date,
        ROW_NUMBER() OVER (
            PARTITION BY COALESCE(NULLIF(e.phone,''), CONCAT('_id:', e.id))
            ORDER BY e.created_at, e.id) AS lrn
    FROM leads_contact_event_logs e
    WHERE e.deleted_at IS NULL
      AND e.event_type = 'contact_submitted'
      AND e.created_at >= {{from_date}}
      AND e.created_at <  DATE_ADD({{to_date}}, INTERVAL 1 DAY)
),
daily AS (
    SELECT capture_date, COUNT(*) AS leads
    FROM deduped WHERE lrn = 1
    GROUP BY 1
)
SELECT
    d.capture_date,
    CASE
      WHEN {{cohort_days}} >= 9999
           THEN 'Counted · Till date (no gate)'
      WHEN DATE_ADD(d.capture_date, INTERVAL {{cohort_days}} DAY) <= CURDATE()
           THEN 'Counted'
      ELSE 'Dropped · window not closed'
    END                                                              AS status,
    CASE WHEN {{cohort_days}} >= 9999 THEN CURDATE()
         ELSE DATE_ADD(d.capture_date, INTERVAL {{cohort_days}} DAY)
    END                                                              AS window_closes,
    -- how many more days before this date becomes countable
    CASE WHEN {{cohort_days}} >= 9999 THEN 0
         ELSE GREATEST(DATEDIFF(DATE_ADD(d.capture_date, INTERVAL {{cohort_days}} DAY),
                                CURDATE()), 0)
    END                                                              AS days_until_counted,
    d.leads                                                          AS leads_on_date,
    CASE WHEN {{cohort_days}} >= 9999
           OR DATE_ADD(d.capture_date, INTERVAL {{cohort_days}} DAY) <= CURDATE()
         THEN d.leads ELSE 0 END                                     AS leads_counted,
    CASE WHEN {{cohort_days}} < 9999
          AND DATE_ADD(d.capture_date, INTERVAL {{cohort_days}} DAY) > CURDATE()
         THEN d.leads ELSE 0 END                                     AS leads_dropped
FROM daily d
ORDER BY d.capture_date;


-- ============================================================
-- COMPANION SUMMARY CARD — save separately, use a Number or Detail card
-- Answers "how much am I not seeing?" in one line.
-- ============================================================
/*
WITH deduped AS (
    SELECT DATE(e.created_at) AS capture_date,
           ROW_NUMBER() OVER (
               PARTITION BY COALESCE(NULLIF(e.phone,''), CONCAT('_id:', e.id))
               ORDER BY e.created_at, e.id) AS lrn
    FROM leads_contact_event_logs e
    WHERE e.deleted_at IS NULL AND e.event_type = 'contact_submitted'
      AND e.created_at >= {{from_date}}
      AND e.created_at <  DATE_ADD({{to_date}}, INTERVAL 1 DAY)
),
daily AS (
    SELECT capture_date, COUNT(*) AS leads FROM deduped WHERE lrn = 1 GROUP BY 1
)
SELECT
    COUNT(*)                                                         AS capture_dates_in_range,
    SUM(CASE WHEN {{cohort_days}} >= 9999
              OR DATE_ADD(capture_date, INTERVAL {{cohort_days}} DAY) <= CURDATE()
             THEN 1 ELSE 0 END)                                      AS dates_counted,
    SUM(leads)                                                       AS leads_in_range,
    SUM(CASE WHEN {{cohort_days}} >= 9999
              OR DATE_ADD(capture_date, INTERVAL {{cohort_days}} DAY) <= CURDATE()
             THEN leads ELSE 0 END)                                  AS leads_counted,
    ROUND(100 * SUM(CASE WHEN {{cohort_days}} >= 9999
                          OR DATE_ADD(capture_date, INTERVAL {{cohort_days}} DAY) <= CURDATE()
                         THEN leads ELSE 0 END)
              / NULLIF(SUM(leads),0), 1)                             AS pct_leads_counted
FROM daily;
*/
