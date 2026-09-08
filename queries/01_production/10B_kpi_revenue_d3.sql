-- ============================================================
-- 10B · KPI TILES — CONVERSIONS & REVENUE (Pinned to Fixed D3 Window)
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
),

scoped_parents AS (
    SELECT DISTINCT parent_id FROM lead_by_parent
),

sched_pool AS (
    SELECT csb.id AS booking_id, csb.parent_id, csb.leads_contact_utm_id,
           DATE(cs.class_date) AS class_date,
           csb.attended_class
    FROM classschedulebookings csb
    JOIN classschedules cs ON csb.classschedule_id = cs.id AND cs.deleted_at IS NULL
    JOIN classes c         ON cs.class_id = c.id           AND c.deleted_at IS NULL
    WHERE csb.deleted_at IS NULL
      AND csb.demo_class = 'Yes' AND csb.is_cancelled = 'No'
      AND c.category_id <> '31' AND c.is_workshop = 'no'
      AND c.class_name NOT LIKE '%MOCK DEMO%' AND c.class_name NOT LIKE '%TEACHER NAME%'
      AND cs.class_date >= {{from_date}}
      AND cs.class_date <  DATE_ADD(
              LEAST(CURDATE(), DATE_ADD({{to_date}}, INTERVAL 3 DAY)),
              INTERVAL 1 DAY)
),

sched_attr AS (
    SELECT cl.capture_date, cl.source_campaign, cl.ad_key,
           sp.booking_id, sp.attended_class
    FROM sched_pool sp
    JOIN cohort_leads cl
           ON cl.lead_key = sp.leads_contact_utm_id
          AND sp.class_date BETWEEN cl.capture_date AND cl.window_end
    UNION ALL
    SELECT lbp.capture_date, lbp.source_campaign, lbp.ad_key,
           sp.booking_id, sp.attended_class
    FROM sched_pool sp
    LEFT JOIN cohort_leads c2 ON c2.lead_key = sp.leads_contact_utm_id
    JOIN lead_by_parent lbp
           ON lbp.parent_id = sp.parent_id
          AND sp.class_date BETWEEN lbp.capture_date AND lbp.window_end
    WHERE c2.lead_key IS NULL
),

Demo_Scheduled AS (
    SELECT
        COUNT(DISTINCT booking_id)                                           AS demos_scheduled,
        COUNT(DISTINCT CASE WHEN attended_class='Yes' THEN booking_id END)   AS demos_attended
    FROM sched_attr
),

prior AS (
    SELECT i.parent_id, MIN(DATE(i.created_at)) AS first_invoice
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
                   AND DATE(i.created_at) BETWEEN lbp.capture_date AND lbp.window_end
    LEFT JOIN currencies curr ON i.currency = curr.currency
    LEFT JOIN prior pr ON pr.parent_id = i.parent_id
                      AND pr.first_invoice < lbp.capture_date
    WHERE i.type_of_booking IN ('New','Token')
),

-- Spend restricted to D3 mature capture dates
fb_ad AS (
    SELECT SUM(a.spend) AS spend_in_d3_window
    FROM facebookads a
    LEFT JOIN ( SELECT campaign_code, MIN(country_code) AS country_code
                FROM onlinecampaigns GROUP BY campaign_code ) b
           ON a.campaign_name = b.campaign_code
    WHERE a.capture_date >= {{from_date}}
      AND a.capture_date <  DATE_ADD({{to_date}}, INTERVAL 1 DAY)
      AND DATE_ADD(DATE(a.capture_date), INTERVAL 3 DAY) <= CURDATE()
      [[AND a.campaign_name IN ({{campaign_nm}})]]
      [[AND b.country_code IN ({{country_cd}})]]
)

SELECT
    ROUND(100.0 * (SELECT conversions_first_time FROM Converted)
          / NULLIF((SELECT demos_attended FROM Demo_Scheduled),0), 2) AS conversion_pct,
    ROUND((SELECT new_revenue_first_time FROM Converted)
          / NULLIF((SELECT spend_in_d3_window FROM fb_ad),0), 2)     AS roas,
    ROUND((SELECT new_revenue_first_time FROM Converted)
          / NULLIF((SELECT conversions_first_time FROM Converted),0)) AS arpu,
    (SELECT COUNT(DISTINCT lead_key) FROM cohort_leads)              AS contacts_in_d3_window,
    (SELECT spend_in_d3_window FROM fb_ad)                           AS spend_in_d3_window,
    (SELECT conversions_first_time FROM Converted)                   AS conversions_in_d3_window,
    (SELECT new_revenue_first_time FROM Converted)                   AS revenue_in_d3_window;


-- ============================================================
-- WINDOW MATURITY AUDIT QUERY
-- Check how many capture dates are available for each window size
-- ============================================================
/*
SELECT
    'D0' AS window, COUNT(DISTINCT DATE(created_at)) AS mature_dates FROM leads_contact_event_logs
    WHERE created_at >= '2026-08-07' AND DATE(created_at) <= CURDATE()
UNION ALL
SELECT 'D1', COUNT(DISTINCT DATE(created_at)) FROM leads_contact_event_logs
    WHERE created_at >= '2026-08-07' AND DATE_ADD(DATE(created_at), INTERVAL 1 DAY) <= CURDATE()
UNION ALL
SELECT 'D3', COUNT(DISTINCT DATE(created_at)) FROM leads_contact_event_logs
    WHERE created_at >= '2026-08-07' AND DATE_ADD(DATE(created_at), INTERVAL 3 DAY) <= CURDATE()
UNION ALL
SELECT 'D7', COUNT(DISTINCT DATE(created_at)) FROM leads_contact_event_logs
    WHERE created_at >= '2026-08-07' AND DATE_ADD(DATE(created_at), INTERVAL 7 DAY) <= CURDATE();
*/
