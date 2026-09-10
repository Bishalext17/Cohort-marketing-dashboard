-- ============================================================
-- 10B · KPI TILES — CONVERSIONS & REVENUE (Pinned to Fixed D3 Window) [HYPER-OPTIMISED]
-- Powers Tiles 6–8: Conversion % · D3, Paid ROAS · D3, ARPU · D3
--
-- CRITICAL WIRING RULE:
--   DO NOT connect the dashboard cohort filter to this question.
--   The window is hard-coded to 3 days so leads have equal maturity.
--
-- Variables:
--   from_date    Date · Required · default 2026-08-07
--   to_date      Date · Required
--   campaign_nm  Text · Optional · multi-select
--   country_cd   Text · Optional
-- ============================================================

WITH
cohort_leads AS (
    SELECT lead_key, mobile, capture_date, source_campaign, ad_key,
           placement, lead_country, window_end
    FROM (
        SELECT
            e.id                                                 AS lead_key,
            NULLIF(e.phone,'')                                   AS mobile,
            e.country_code                                       AS lead_country,
            DATE(e.created_at)                                   AS capture_date,
            COALESCE(NULLIF(e.utm_campaign,''),'NA')             AS source_campaign,
            NULLIF(e.utm_content,'')                             AS ad_key,
            COALESCE(NULLIF(e.utm_placement,''),'Not Available') AS placement,
            DATE_ADD(DATE(e.created_at), INTERVAL 3 DAY)        AS window_end,
            ROW_NUMBER() OVER (
                PARTITION BY COALESCE(NULLIF(e.phone,''), CONCAT('_id:', e.id))
                ORDER BY e.created_at, e.id)                     AS lrn
        FROM leads_contact_event_logs e
        WHERE e.deleted_at IS NULL
          AND e.event_type = 'contact_submitted'
          AND e.created_at >= {{from_date}}
          AND e.created_at <  DATE_ADD({{to_date}}, INTERVAL 1 DAY)
          -- Hard-coded D3 Maturity Gate:
          AND DATE_ADD(DATE(e.created_at), INTERVAL 3 DAY) <= CURDATE()
          [[AND COALESCE(NULLIF(e.utm_campaign,''),'NA') IN ({{campaign_nm}})]]
          [[AND e.country_code IN ({{country_cd}})]]
    ) t
    WHERE lrn = 1
),

lead_by_parent AS (
    SELECT p.id AS parent_id, cl.capture_date, cl.source_campaign,
           cl.ad_key, cl.window_end
    FROM cohort_leads cl
    JOIN parents p ON p.mobile_number = cl.mobile AND p.deleted_at IS NULL
    WHERE cl.mobile IS NOT NULL
),

scoped_parents AS (
    SELECT DISTINCT parent_id FROM lead_by_parent
),

-- Scoped schedules by Lead UTM ID (index seek)
sched_pool_utm AS (
    SELECT
        cl.capture_date, cl.source_campaign, cl.ad_key,
        csb.id AS booking_id, csb.attended_class
    FROM cohort_leads cl
    JOIN classschedulebookings csb ON csb.leads_contact_utm_id = cl.lead_key AND csb.deleted_at IS NULL
    JOIN classschedules cs ON csb.classschedule_id = cs.id AND cs.deleted_at IS NULL
    JOIN classes c ON cs.class_id = c.id AND c.deleted_at IS NULL
    WHERE csb.demo_class = 'Yes' AND csb.is_cancelled = 'No'
      AND c.category_id <> '31' AND c.is_workshop = 'no'
      AND c.class_name NOT LIKE '%MOCK DEMO%' AND c.class_name NOT LIKE '%TEACHER NAME%'
      AND cs.class_date >= CAST(cl.capture_date AS DATETIME)
      AND cs.class_date <  DATE_ADD(CAST(cl.window_end AS DATETIME), INTERVAL 1 DAY)
),

-- Scoped schedules by Parent Mobile (index seek)
sched_pool_parent AS (
    SELECT
        lbp.capture_date, lbp.source_campaign, lbp.ad_key,
        csb.id AS booking_id, csb.attended_class
    FROM lead_by_parent lbp
    JOIN classschedulebookings csb ON csb.parent_id = lbp.parent_id AND csb.deleted_at IS NULL
    JOIN classschedules cs ON csb.classschedule_id = cs.id AND cs.deleted_at IS NULL
    JOIN classes c ON cs.class_id = c.id AND c.deleted_at IS NULL
    LEFT JOIN cohort_leads c2 ON c2.lead_key = csb.leads_contact_utm_id
    WHERE csb.demo_class = 'Yes' AND csb.is_cancelled = 'No'
      AND c.category_id <> '31' AND c.is_workshop = 'no'
      AND c.class_name NOT LIKE '%MOCK DEMO%' AND c.class_name NOT LIKE '%TEACHER NAME%'
      AND cs.class_date >= CAST(lbp.capture_date AS DATETIME)
      AND cs.class_date <  DATE_ADD(CAST(lbp.window_end AS DATETIME), INTERVAL 1 DAY)
      AND c2.lead_key IS NULL
),

sched_attr AS (
    SELECT * FROM sched_pool_utm
    UNION ALL
    SELECT * FROM sched_pool_parent
),

Demo_Scheduled AS (
    SELECT
        COUNT(DISTINCT booking_id)                                         AS demos_scheduled,
        COUNT(DISTINCT CASE WHEN attended_class='Yes' THEN booking_id END) AS demos_attended
    FROM sched_attr
),

prior AS (
    SELECT i.parent_id, MIN(i.created_at) AS first_invoice_ts
    FROM invoices i
    JOIN scoped_parents sp ON sp.parent_id = i.parent_id
    WHERE i.invoice_type = 'regular'
    GROUP BY 1
),

Converted AS (
    SELECT
        COUNT(DISTINCT CASE WHEN i.type_of_booking IN ('New','Token')
                             AND i.invoice_type='regular'
                             AND pr.parent_id IS NULL
                            THEN i.parent_id END)                        AS conversions_first_time,
        SUM(CASE WHEN i.type_of_booking='New' AND i.invoice_type='regular'
                  AND pr.parent_id IS NULL
                 THEN CASE WHEN i.currency='INR' THEN i.amount
                      ELSE i.amount * 78 / NULLIF(curr.conversion_factor,0) END
                 ELSE 0 END)                                             AS new_revenue_first_time
    FROM lead_by_parent lbp
    JOIN invoices i ON i.parent_id = lbp.parent_id
                   AND i.created_at >= CAST(lbp.capture_date AS DATETIME)
                   AND i.created_at <  DATE_ADD(CAST(lbp.window_end AS DATETIME), INTERVAL 1 DAY)
    LEFT JOIN currencies curr ON i.currency = curr.currency
    LEFT JOIN prior pr ON pr.parent_id = i.parent_id
                      AND pr.first_invoice_ts < CAST(lbp.capture_date AS DATETIME)
    WHERE i.type_of_booking IN ('New','Token')
),

-- Spend restricted to D3 mature capture dates
fb_ad AS (
    SELECT COALESCE(SUM(a.spend),0) AS spend_in_d3_window
    FROM facebookads a
    LEFT JOIN ( SELECT campaign_code, MIN(country_code) AS country_code
                FROM onlinecampaigns GROUP BY campaign_code ) b
           ON a.campaign_name = b.campaign_code
    WHERE a.capture_date >= {{from_date}}
      AND a.capture_date <  DATE_ADD({{to_date}}, INTERVAL 1 DAY)
      AND DATE_ADD(DATE(a.capture_date), INTERVAL 3 DAY) <= CURDATE()
      [[AND a.campaign_name IN ({{campaign_nm}})]]
      [[AND b.country_code IN ({{country_cd}})]]
),

lead_counts AS (
    SELECT COUNT(DISTINCT lead_key) AS contacts_in_d3_window
    FROM cohort_leads
)

SELECT
    ROUND(100.0 * cv.conversions_first_time / NULLIF(ds.demos_attended,0), 2) AS conversion_pct,
    ROUND(cv.new_revenue_first_time / NULLIF(fb.spend_in_d3_window,0), 2)     AS roas,
    ROUND(cv.new_revenue_first_time / NULLIF(cv.conversions_first_time,0))    AS arpu,
    lc.contacts_in_d3_window,
    fb.spend_in_d3_window,
    cv.conversions_first_time                                                AS conversions_in_d3_window,
    cv.new_revenue_first_time                                                AS revenue_in_d3_window
FROM Converted cv
CROSS JOIN Demo_Scheduled ds
CROSS JOIN fb_ad fb
CROSS JOIN lead_counts lc;
