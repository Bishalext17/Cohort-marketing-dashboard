-- ============================================================
-- 10A · KPI TILES — VOLUME & COST [HYPER-OPTIMISED]
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
    WHERE cl.mobile IS NOT NULL
),

scoped_parents AS (
    SELECT DISTINCT parent_id FROM lead_by_parent
),

-- Scoped bookings by Lead UTM ID (index seek)
book_pool_utm AS (
    SELECT
        cl.capture_date, cl.source_campaign, cl.ad_key,
        csb.id AS booking_id, csb.is_cancelled, csb.attended_class,
        DATE(cs.class_date) AS class_date
    FROM cohort_leads cl
    JOIN classschedulebookings csb ON csb.leads_contact_utm_id = cl.lead_key AND csb.deleted_at IS NULL
    JOIN classschedules cs ON csb.classschedule_id = cs.id AND cs.deleted_at IS NULL
    JOIN classes c ON cs.class_id = c.id AND c.deleted_at IS NULL
    WHERE csb.demo_class = 'Yes'
      AND c.category_id <> '31' AND c.is_workshop = 'no'
      AND c.class_name NOT LIKE '%MOCK DEMO%' AND c.class_name NOT LIKE '%TEACHER NAME%'
      AND csb.created_at >= CAST(cl.capture_date AS DATETIME)
      AND csb.created_at <  DATE_ADD(CAST(cl.window_end AS DATETIME), INTERVAL 1 DAY)
),

-- Scoped bookings by Parent Mobile (index seek)
book_pool_parent AS (
    SELECT
        lbp.capture_date, lbp.source_campaign, lbp.ad_key,
        csb.id AS booking_id, csb.is_cancelled, csb.attended_class,
        DATE(cs.class_date) AS class_date
    FROM lead_by_parent lbp
    JOIN classschedulebookings csb ON csb.parent_id = lbp.parent_id AND csb.deleted_at IS NULL
    JOIN classschedules cs ON csb.classschedule_id = cs.id AND cs.deleted_at IS NULL
    JOIN classes c ON cs.class_id = c.id AND c.deleted_at IS NULL
    LEFT JOIN cohort_leads c2 ON c2.lead_key = csb.leads_contact_utm_id
    WHERE csb.demo_class = 'Yes'
      AND c.category_id <> '31' AND c.is_workshop = 'no'
      AND c.class_name NOT LIKE '%MOCK DEMO%' AND c.class_name NOT LIKE '%TEACHER NAME%'
      AND csb.created_at >= CAST(lbp.capture_date AS DATETIME)
      AND csb.created_at <  DATE_ADD(CAST(lbp.window_end AS DATETIME), INTERVAL 1 DAY)
      AND c2.lead_key IS NULL
),

book_attr AS (
    SELECT * FROM book_pool_utm
    UNION ALL
    SELECT * FROM book_pool_parent
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

lead_counts AS (
    SELECT COUNT(DISTINCT lead_key) AS leads
    FROM cohort_leads
),

Demo_Bookings AS (
    SELECT COUNT(DISTINCT CASE WHEN is_cancelled='No' THEN booking_id END) AS demos_booked
    FROM book_attr
),

Demo_Scheduled AS (
    SELECT
        COUNT(DISTINCT booking_id)                                         AS demos_scheduled,
        COUNT(DISTINCT CASE WHEN attended_class='Yes' THEN booking_id END) AS demos_attended
    FROM sched_attr
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
),

fb_total AS (
    SELECT COALESCE(SUM(spend),0) AS total_spend FROM fb_ad
)

SELECT
    ROUND(f.total_spend)                                             AS spend,
    lc.leads                                                         AS contacts,
    ROUND(f.total_spend / NULLIF(lc.leads,0))                       AS cpl,
    db.demos_booked                                                  AS demos_booked,
    ROUND(100.0 * ds.demos_attended / NULLIF(ds.demos_scheduled,0), 1) AS show_up_rate_pct
FROM fb_total f
CROSS JOIN lead_counts lc
CROSS JOIN Demo_Bookings db
CROSS JOIN Demo_Scheduled ds;
