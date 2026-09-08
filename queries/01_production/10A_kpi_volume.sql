-- ============================================================
-- 10A · KPI TILES — VOLUME & COST (follows cohort filter)
-- Powers Tiles 1–5: Paid Spend, Paid Leads, Paid CPL, Demos Booked, Show-up %
--
-- Variables:
--   cohort_days  Number · Required · wire to dashboard cohort filter
--   from_date    Date   · Required · default 2026-08-07
--   to_date      Date   · Required
--   campaign_nm  Text   · Optional · multi-select
--   country_cd   Text   · Optional
--   ad_nm        Text   · Optional
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
            CASE WHEN {{cohort_days}} >= 9999 THEN CURDATE()
                 ELSE DATE_ADD(DATE(e.created_at), INTERVAL {{cohort_days}} DAY)
            END                                                  AS window_end,
            ROW_NUMBER() OVER (
                PARTITION BY COALESCE(NULLIF(e.phone,''), CONCAT('_id:', e.id))
                ORDER BY e.created_at, e.id)                     AS lrn
        FROM leads_contact_event_logs e
        WHERE e.deleted_at IS NULL
          AND e.event_type = 'contact_submitted'
          AND e.created_at >= {{from_date}}
          AND e.created_at <  DATE_ADD({{to_date}}, INTERVAL 1 DAY)
          AND ( {{cohort_days}} >= 9999
                OR DATE_ADD(DATE(e.created_at), INTERVAL {{cohort_days}} DAY) <= CURDATE() )
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

book_pool AS (
    SELECT csb.id AS booking_id, csb.parent_id, csb.leads_contact_utm_id,
           DATE(csb.created_at) AS booked_date,
           DATE(cs.class_date)  AS class_date,
           csb.is_cancelled, csb.attended_class
    FROM classschedulebookings csb
    JOIN classschedules cs ON csb.classschedule_id = cs.id AND cs.deleted_at IS NULL
    JOIN classes c         ON cs.class_id = c.id           AND c.deleted_at IS NULL
    WHERE csb.deleted_at IS NULL
      AND csb.demo_class = 'Yes'
      AND c.category_id <> '31' AND c.is_workshop = 'no'
      AND c.class_name NOT LIKE '%MOCK DEMO%' AND c.class_name NOT LIKE '%TEACHER NAME%'
      AND csb.created_at >= {{from_date}}
      AND csb.created_at <  DATE_ADD(
              LEAST(CURDATE(),
                    CASE WHEN {{cohort_days}} >= 9999 THEN CURDATE()
                         ELSE DATE_ADD({{to_date}}, INTERVAL {{cohort_days}} DAY) END),
              INTERVAL 1 DAY)
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
              LEAST(CURDATE(),
                    CASE WHEN {{cohort_days}} >= 9999 THEN CURDATE()
                         ELSE DATE_ADD({{to_date}}, INTERVAL {{cohort_days}} DAY) END),
              INTERVAL 1 DAY)
),

book_attr AS (
    SELECT cl.capture_date, cl.source_campaign, cl.ad_key,
           bp.booking_id, bp.is_cancelled, bp.attended_class, bp.class_date
    FROM book_pool bp
    JOIN cohort_leads cl
           ON cl.lead_key = bp.leads_contact_utm_id
          AND bp.booked_date BETWEEN cl.capture_date AND cl.window_end
    UNION ALL
    SELECT lbp.capture_date, lbp.source_campaign, lbp.ad_key,
           bp.booking_id, bp.is_cancelled, bp.attended_class, bp.class_date
    FROM book_pool bp
    LEFT JOIN cohort_leads c2 ON c2.lead_key = bp.leads_contact_utm_id
    JOIN lead_by_parent lbp
           ON lbp.parent_id = bp.parent_id
          AND bp.booked_date BETWEEN lbp.capture_date AND lbp.window_end
    WHERE c2.lead_key IS NULL
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

lead_counts AS (
    SELECT capture_date, source_campaign, ad_key,
           COUNT(DISTINCT lead_key) AS leads
    FROM cohort_leads
    GROUP BY 1,2,3
),

Demo_Bookings AS (
    SELECT capture_date, source_campaign, ad_key,
        COUNT(DISTINCT CASE WHEN is_cancelled='No' THEN booking_id END)      AS demos_booked
    FROM book_attr
    GROUP BY 1,2,3
),

Demo_Scheduled AS (
    SELECT capture_date, source_campaign, ad_key,
        COUNT(DISTINCT booking_id)                                           AS demos_scheduled,
        COUNT(DISTINCT CASE WHEN attended_class='Yes' THEN booking_id END)   AS demos_attended
    FROM sched_attr
    GROUP BY 1,2,3
),

fb_ad AS (
    SELECT
        DATE(a.capture_date)                     AS d1,
        b.country_code,
        a.campaign_id, a.campaign_name,
        COALESCE(a.ad_name,'Not Available')      AS ad_name,
        SUM(a.spend)                             AS spend
    FROM facebookads a
    LEFT JOIN ( SELECT campaign_code, MIN(country_code) AS country_code
                FROM onlinecampaigns GROUP BY campaign_code ) b
           ON a.campaign_name = b.campaign_code
    WHERE a.capture_date >= {{from_date}}
      AND a.capture_date <  DATE_ADD({{to_date}}, INTERVAL 1 DAY)
      AND ( {{cohort_days}} >= 9999
            OR DATE_ADD(DATE(a.capture_date), INTERVAL {{cohort_days}} DAY) <= CURDATE() )
      [[AND a.campaign_name IN ({{campaign_nm}})]]
      [[AND b.country_code IN ({{country_cd}})]]
    GROUP BY 1,2,3,4,5
)

SELECT
    ROUND(SUM(fb.spend))                                             AS spend,
    (SELECT COALESCE(SUM(leads),0) FROM lead_counts)                 AS contacts,
    ROUND(SUM(fb.spend) / NULLIF((SELECT SUM(leads) FROM lead_counts),0)) AS cpl,
    (SELECT COALESCE(SUM(demos_booked),0) FROM Demo_Bookings)        AS demos_booked,
    ROUND(100.0 * (SELECT SUM(demos_attended) FROM Demo_Scheduled)
          / NULLIF((SELECT SUM(demos_scheduled) FROM Demo_Scheduled),0), 1) AS show_up_rate_pct
FROM fb_ad fb;
