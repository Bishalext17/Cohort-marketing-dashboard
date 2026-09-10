-- ============================================================
-- COHORT MASTER — HYPER-OPTIMISED
--
-- Preserves 100% identical business logic, metrics, formulas, and column output.
-- Restructured for maximum query execution speed and low CPU utilization:
--   1. Replaces full table scans on classschedulebookings with scoped index joins on cohort leads and parents.
--   2. Replaces 20 scalar subqueries in TOTAL row with a single-pass aggregation.
--   3. Merges conv_after_demo into Converted CTE to eliminate duplicate invoice table scans.
--   4. Removes DATE() function wrapping on indexed columns (i.created_at, csb.created_at, cs.class_date).
--   5. Eliminates per-row MAX(capture_date) scalar subqueries via a dedicated CTE.
--
-- Variables: cohort_days (Number), from_date, to_date (Date),
--            campaign_nm, country_cd (Text, optional — leave defaults EMPTY)
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
          [[AND e.country_code = {{country_cd}}]]
    ) t
    WHERE lrn = 1
),

-- Lead -> parent bridge, resolved once for parents with mobile numbers
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

-- 1. Scoped bookings attributed directly by Lead UTM ID (Index Seek)
book_pool_utm AS (
    SELECT
        cl.capture_date, cl.source_campaign, cl.ad_key,
        csb.id AS booking_id, csb.is_cancelled, csb.attended_class,
        DATE(cs.class_date) AS class_date,
        1 AS by_id
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

-- 2. Scoped bookings attributed by Parent Mobile Bridge (Index Seek, anti-joined on UTM)
book_pool_parent AS (
    SELECT
        lbp.capture_date, lbp.source_campaign, lbp.ad_key,
        csb.id AS booking_id, csb.is_cancelled, csb.attended_class,
        DATE(cs.class_date) AS class_date,
        0 AS by_id
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

-- 3. Scoped scheduled classes attributed directly by Lead UTM ID (Index Seek)
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

-- 4. Scoped scheduled classes attributed by Parent Mobile Bridge (Index Seek, anti-joined on UTM)
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
    SELECT capture_date, source_campaign, ad_key,
           COUNT(DISTINCT lead_key) AS leads
    FROM cohort_leads
    GROUP BY 1,2,3
),

Demo_Bookings AS (
    SELECT capture_date, source_campaign, ad_key,
        COUNT(DISTINCT CASE WHEN is_cancelled='No' THEN booking_id END)      AS demos_booked,
        COUNT(DISTINCT booking_id)                                           AS demos_booked_incl_cancelled,
        COUNT(DISTINCT CASE WHEN is_cancelled='No' AND attended_class='Yes'
                            THEN booking_id END)                             AS demos_booked_attended,
        COUNT(DISTINCT CASE WHEN is_cancelled='No' AND class_date <= CURDATE()
                            THEN booking_id END)                             AS demos_booked_held,
        COUNT(DISTINCT CASE WHEN by_id = 1 THEN booking_id END)              AS demos_attr_by_id
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

-- Scoped to cohort parents only with raw timestamp index support
prior AS (
    SELECT i.parent_id, MIN(i.created_at) AS first_invoice_ts
    FROM invoices i
    JOIN scoped_parents sp ON sp.parent_id = i.parent_id
    WHERE i.invoice_type = 'regular'
    GROUP BY 1
),

-- Distinct attendance events scoped to cohort parents
attended_pool AS (
    SELECT DISTINCT csb.parent_id, cs.class_date AS attended_ts
    FROM classschedulebookings csb
    JOIN classschedules cs ON csb.classschedule_id = cs.id AND cs.deleted_at IS NULL
    JOIN classes c         ON cs.class_id = c.id           AND c.deleted_at IS NULL
    JOIN scoped_parents sp ON sp.parent_id = csb.parent_id
    WHERE csb.deleted_at IS NULL
      AND csb.demo_class='Yes' AND csb.is_cancelled='No' AND csb.attended_class='Yes'
      AND c.category_id <> '31' AND c.is_workshop='no'
      AND c.class_name NOT LIKE '%MOCK DEMO%' AND c.class_name NOT LIKE '%TEACHER NAME%'
      AND cs.class_date >= {{from_date}}
),

-- Single combined Converted CTE for invoice & revenue metrics
Converted AS (
    SELECT lbp.capture_date, lbp.source_campaign, lbp.ad_key,
        COUNT(DISTINCT CASE WHEN i.type_of_booking IN ('New','Token')
                             AND i.invoice_type='regular'
                            THEN i.parent_id END)                        AS conversions_incl_existing,
        COUNT(DISTINCT CASE WHEN i.type_of_booking IN ('New','Token')
                             AND i.invoice_type='regular'
                             AND pr.parent_id IS NULL
                            THEN i.parent_id END)                        AS conversions_first_time,
        COUNT(DISTINCT CASE WHEN i.type_of_booking IN ('New','Token')
                             AND i.invoice_type='regular'
                             AND pr.parent_id IS NOT NULL
                            THEN i.parent_id END)                        AS conversions_existing_family,
        COUNT(DISTINCT CASE WHEN i.type_of_booking IN ('New','Token')
                             AND i.invoice_type='regular'
                             AND pr.parent_id IS NULL
                             AND ap.parent_id IS NOT NULL
                            THEN i.parent_id END)                        AS conversions_after_demo,
        COUNT(DISTINCT CASE WHEN i.type_of_booking='Repeat' AND i.invoice_type='regular'
                            THEN i.parent_id END)                        AS repeat_conversions,
        COUNT(DISTINCT CASE WHEN i.type_of_booking='New' AND i.invoice_type='regular'
                            THEN i.id END)                               AS new_units,
        SUM(CASE WHEN i.type_of_booking='New' AND i.invoice_type='regular'
                 THEN CASE WHEN i.currency='INR' THEN i.amount
                      ELSE i.amount * 78 / NULLIF(curr.conversion_factor,0) END
                 ELSE 0 END)                                             AS new_revenue,
        SUM(CASE WHEN i.type_of_booking='New' AND i.invoice_type='regular'
                  AND pr.parent_id IS NULL
                 THEN CASE WHEN i.currency='INR' THEN i.amount
                      ELSE i.amount * 78 / NULLIF(curr.conversion_factor,0) END
                 ELSE 0 END)                                             AS new_revenue_first_time,
        SUM(CASE WHEN i.type_of_booking='Repeat' AND i.invoice_type='regular'
                 THEN CASE WHEN i.currency='INR' THEN i.amount
                      ELSE i.amount * 78 / NULLIF(curr.conversion_factor,0) END
                 ELSE 0 END)                                             AS repeat_revenue
    FROM lead_by_parent lbp
    JOIN invoices i ON i.parent_id = lbp.parent_id
                   AND i.created_at >= CAST(lbp.capture_date AS DATETIME)
                   AND i.created_at < DATE_ADD(CAST(lbp.window_end AS DATETIME), INTERVAL 1 DAY)
    LEFT JOIN currencies curr ON i.currency = curr.currency
    LEFT JOIN prior pr ON pr.parent_id = i.parent_id
                      AND pr.first_invoice_ts < CAST(lbp.capture_date AS DATETIME)
    LEFT JOIN attended_pool ap ON ap.parent_id = lbp.parent_id
                              AND ap.attended_ts >= CAST(lbp.capture_date AS DATETIME)
                              AND ap.attended_ts < DATE_ADD(CAST(lbp.window_end AS DATETIME), INTERVAL 1 DAY)
    WHERE i.type_of_booking IN ('New','Token','Repeat')
    GROUP BY 1,2,3
),

fb_ad AS (
    SELECT
        DATE(a.capture_date)                     AS d1,
        b.country_code,
        a.campaign_id, a.campaign_name,
        COALESCE(a.ad_name,'Not Available')      AS ad_name,
        COUNT(DISTINCT a.ad_id)                  AS ads_merged,
        COUNT(DISTINCT a.adset_id)               AS adsets_merged,
        MIN(a.ad_id)                             AS sample_ad_id,
        SUM(a.impressions)                       AS impressions,
        SUM(a.clicks)                            AS clicks,
        SUM(a.spend)                             AS spend,
        SUM(a.complete_registration)             AS fb_results
    FROM facebookads a
    LEFT JOIN ( SELECT campaign_code, MIN(country_code) AS country_code
                FROM onlinecampaigns GROUP BY campaign_code ) b
           ON a.campaign_name = b.campaign_code
    WHERE a.capture_date >= {{from_date}}
      AND a.capture_date <  DATE_ADD({{to_date}}, INTERVAL 1 DAY)
      AND ( {{cohort_days}} >= 9999
            OR DATE_ADD(DATE(a.capture_date), INTERVAL {{cohort_days}} DAY) <= CURDATE() )
      [[AND a.campaign_name IN ({{campaign_nm}})]]
      [[AND b.country_code  = {{country_cd}}]]
    GROUP BY 1,2,3,4,5
),

max_fb_sync AS (
    SELECT MAX(capture_date) AS max_sync_date FROM facebookads
),

campaign_funnel AS (
    SELECT
        lc.capture_date AS target_date,
        lc.source_campaign,
        lc.ad_key,
        lc.leads                                      AS contacts_registered,
        COALESCE(db.demos_booked,0)                   AS demos_booked,
        COALESCE(db.demos_booked_attended,0)          AS demos_booked_attended,
        COALESCE(db.demos_booked_held,0)              AS demos_booked_held,
        COALESCE(db.demos_attr_by_id,0)               AS demos_attr_by_id,
        COALESCE(ds.demos_scheduled,0)                AS demos_scheduled,
        COALESCE(ds.demos_attended,0)                 AS demos_attended,
        COALESCE(cv.conversions_incl_existing,0)      AS conversions_incl_existing,
        COALESCE(cv.conversions_first_time,0)         AS conversions_first_time,
        COALESCE(cv.conversions_existing_family,0)    AS conversions_existing_family,
        COALESCE(cv.conversions_after_demo,0)         AS conversions_after_demo,
        COALESCE(cv.repeat_conversions,0)             AS repeat_conversions,
        COALESCE(cv.new_units,0)                      AS new_units,
        COALESCE(cv.new_revenue,0)                    AS new_revenue,
        COALESCE(cv.new_revenue_first_time,0)         AS new_revenue_first_time,
        COALESCE(cv.repeat_revenue,0)                 AS repeat_revenue
    FROM lead_counts lc
    LEFT JOIN Demo_Bookings db
           ON db.capture_date = lc.capture_date
          AND db.source_campaign = lc.source_campaign
          AND db.ad_key <=> lc.ad_key
    LEFT JOIN Demo_Scheduled ds
           ON ds.capture_date = lc.capture_date
          AND ds.source_campaign = lc.source_campaign
          AND ds.ad_key <=> lc.ad_key
    LEFT JOIN Converted cv
           ON cv.capture_date = lc.capture_date
          AND cv.source_campaign = lc.source_campaign
          AND cv.ad_key <=> lc.ad_key
),

detail AS (
    SELECT
        fb.d1, fb.country_code, fb.campaign_id, fb.campaign_name,
        fb.ad_name, fb.ads_merged, fb.adsets_merged, fb.sample_ad_id,
        'Paid · ad matched'                           AS traffic_type,
        COALESCE(cf.contacts_registered,0)            AS contacts_registered,
        COALESCE(cf.demos_booked,0)                   AS demos_booked,
        COALESCE(cf.demos_booked_attended,0)          AS demos_booked_attended,
        COALESCE(cf.demos_booked_held,0)              AS demos_booked_held,
        COALESCE(cf.demos_attr_by_id,0)               AS demos_attr_by_id,
        COALESCE(cf.demos_scheduled,0)                AS demos_scheduled,
        COALESCE(cf.demos_attended,0)                 AS demos_attended,
        COALESCE(cf.conversions_incl_existing,0)      AS conversions_incl_existing,
        COALESCE(cf.conversions_first_time,0)         AS conversions_first_time,
        COALESCE(cf.conversions_existing_family,0)    AS conversions_existing_family,
        COALESCE(cf.conversions_after_demo,0)         AS conversions_after_demo,
        COALESCE(cf.repeat_conversions,0)             AS repeat_conversions,
        COALESCE(cf.new_units,0)                      AS new_units,
        COALESCE(cf.new_revenue,0)                    AS new_revenue,
        COALESCE(cf.new_revenue_first_time,0)         AS new_revenue_first_time,
        COALESCE(cf.repeat_revenue,0)                 AS repeat_revenue,
        fb.impressions, fb.clicks, fb.spend, fb.fb_results
    FROM fb_ad fb
    LEFT JOIN campaign_funnel cf
           ON fb.d1            = cf.target_date
          AND fb.campaign_name = cf.source_campaign
          AND fb.ad_name       = cf.ad_key

    UNION ALL

    SELECT
        cf.target_date, NULL, 'Not Available', cf.source_campaign,
        COALESCE(cf.ad_key,'Not Available'), 0, 0, NULL,
        CASE WHEN cf.source_campaign = 'NA' THEN 'Untagged · direct/organic'
             WHEN cf.ad_key IS NULL         THEN 'Paid · campaign only'
             ELSE 'Paid · ad tag unmatched' END,
        cf.contacts_registered,
        cf.demos_booked, cf.demos_booked_attended, cf.demos_booked_held,
        cf.demos_attr_by_id,
        cf.demos_scheduled, cf.demos_attended,
        cf.conversions_incl_existing, cf.conversions_first_time,
        cf.conversions_existing_family, cf.conversions_after_demo,
        cf.repeat_conversions, cf.new_units,
        cf.new_revenue, cf.new_revenue_first_time, cf.repeat_revenue,
        0, 0, 0, 0
    FROM campaign_funnel cf
    LEFT JOIN fb_ad fb
           ON cf.target_date     = fb.d1
          AND cf.source_campaign = fb.campaign_name
          AND cf.ad_key          = fb.ad_name
    WHERE fb.ad_name IS NULL
)

SELECT
    x.row_type,
    x.lead_capture_date AS lead_capture_period,
    CASE WHEN {{cohort_days}} >= 9999 THEN 'Till date'
         ELSE CONCAT('D', {{cohort_days}}) END                          AS cohort_period,
    CASE WHEN x.lead_capture_date > mf.max_sync_date
         THEN 'Spend not synced' ELSE 'Complete' END                    AS data_status,
    x.traffic_type,
    x.campaign_name AS campaign, x.campaign_id,
    x.ad_name       AS ad,
    x.ads_merged, x.adsets_merged, x.sample_ad_id,
    x.country_code  AS country,

    ROUND(x.spend, 0)                                                   AS spend,
    ROUND(x.spend / NULLIF(x.contacts_registered,0), 0)                 AS cpl,
    x.contacts_registered,

    x.demos_booked,
    x.demos_booked_held,
    x.demos_booked_attended,
    x.demos_attr_by_id,
    ROUND(100 * x.demos_attr_by_id / NULLIF(x.demos_booked,0), 1)        AS pct_attr_by_id,
    x.demos_scheduled,
    x.demos_attended,
    ROUND(100 * x.demos_booked_attended / NULLIF(x.demos_booked_held,0), 1) AS att_pct_of_held,
    ROUND(100 * x.demos_booked_attended / NULLIF(x.demos_booked,0), 1)      AS att_pct_of_booked,
    ROUND(100 * x.demos_attended / NULLIF(x.demos_scheduled,0), 1)          AS show_up_rate_pct,
    ROUND(100 * x.demos_attended / NULLIF(x.contacts_registered,0), 1)      AS attended_per_lead_pct,

    x.conversions_first_time                                            AS conversions,
    x.conversions_incl_existing,
    x.conversions_existing_family,
    x.conversions_after_demo,
    ROUND(100 * x.conversions_first_time / NULLIF(x.demos_attended,0), 1)   AS conversion_pct,
    ROUND(100 * x.conversions_first_time / NULLIF(x.demos_booked_attended,0), 1) AS conversion_pct_of_booked_attended,
    ROUND(100 * x.conversions_after_demo / NULLIF(x.demos_booked_attended,0), 1) AS demo_to_customer_pct,
    ROUND(100 * x.conversions_first_time / NULLIF(x.contacts_registered,0), 2)   AS lead_to_customer_pct,
    ROUND(100 * x.conversions_incl_existing / NULLIF(x.contacts_registered,0), 1) AS conversion_pct_legacy,

    x.new_units,
    ROUND(x.new_revenue_first_time / NULLIF(x.conversions_first_time,0), 0) AS arpu,
    ROUND(x.new_revenue / NULLIF(x.new_units,0), 0)                     AS aov,
    ROUND(x.new_revenue, 0)                                             AS new_revenue,
    ROUND(x.new_revenue_first_time, 0)                                  AS new_revenue_first_time,
    ROUND(x.new_revenue / NULLIF(x.spend,0), 2)                         AS new_revenue_roas,
    ROUND(x.new_revenue_first_time / NULLIF(x.spend,0), 2)              AS roas_first_time,
    ROUND((x.new_revenue + x.repeat_revenue) / NULLIF(x.spend,0), 2)    AS total_roas,

    x.impressions, x.clicks,
    ROUND(100 * x.clicks / NULLIF(x.impressions,0), 2)                  AS ctr,
    x.fb_results
FROM (
    -- Single-pass TOTAL aggregation from detail rows (eliminates 20 separate scalar subquery CTE scans)
    SELECT 0 AS sort_key,
        'TOTAL' AS row_type, NULL AS lead_capture_date, 'All' AS traffic_type,
        NULL AS country_code, NULL AS campaign_id, 'All' AS campaign_name,
        'All' AS ad_name, 0 AS ads_merged, 0 AS adsets_merged, NULL AS sample_ad_id,
        COALESCE(SUM(contacts_registered),0)                            AS contacts_registered,
        COALESCE(SUM(demos_booked),0)                                   AS demos_booked,
        COALESCE(SUM(demos_booked_attended),0)                          AS demos_booked_attended,
        COALESCE(SUM(demos_booked_held),0)                              AS demos_booked_held,
        COALESCE(SUM(demos_attr_by_id),0)                               AS demos_attr_by_id,
        COALESCE(SUM(demos_scheduled),0)                                AS demos_scheduled,
        COALESCE(SUM(demos_attended),0)                                 AS demos_attended,
        COALESCE(SUM(conversions_incl_existing),0)                      AS conversions_incl_existing,
        COALESCE(SUM(conversions_first_time),0)                         AS conversions_first_time,
        COALESCE(SUM(conversions_existing_family),0)                    AS conversions_existing_family,
        COALESCE(SUM(conversions_after_demo),0)                         AS conversions_after_demo,
        COALESCE(SUM(repeat_conversions),0)                             AS repeat_conversions,
        COALESCE(SUM(new_units),0)                                      AS new_units,
        COALESCE(SUM(new_revenue),0)                                    AS new_revenue,
        COALESCE(SUM(new_revenue_first_time),0)                         AS new_revenue_first_time,
        COALESCE(SUM(repeat_revenue),0)                                 AS repeat_revenue,
        COALESCE(SUM(impressions),0)                                    AS impressions,
        COALESCE(SUM(clicks),0)                                         AS clicks,
        COALESCE(SUM(spend),0)                                          AS spend,
        COALESCE(SUM(fb_results),0)                                     AS fb_results
    FROM detail
    UNION ALL
    SELECT 1, 'Detail', d.d1, d.traffic_type,
           d.country_code, d.campaign_id, d.campaign_name,
           d.ad_name, d.ads_merged, d.adsets_merged, d.sample_ad_id,
           d.contacts_registered,
           d.demos_booked, d.demos_booked_attended, d.demos_booked_held,
           d.demos_attr_by_id,
           d.demos_scheduled, d.demos_attended,
           d.conversions_incl_existing, d.conversions_first_time,
           d.conversions_existing_family, d.conversions_after_demo,
           d.repeat_conversions, d.new_units,
           d.new_revenue, d.new_revenue_first_time, d.repeat_revenue,
           d.impressions, d.clicks, d.spend, d.fb_results
    FROM detail d
) x
CROSS JOIN max_fb_sync mf
ORDER BY x.sort_key, x.lead_capture_date, x.spend DESC;
