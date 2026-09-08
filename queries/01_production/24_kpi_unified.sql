-- KPI TILES — UNIFIED. Matches the master TOTAL row exactly.
--
-- One query for ALL eight tiles. Same CTEs as COHORT_MASTER_OPTIMISED, and no
-- scope filter by default — so every tile equals the master TOTAL row for the
-- same cohort_days / from_date / to_date. Wire cohort_days to the dashboard
-- filter on every tile.
--
-- Variables:
--   cohort_days  Number · Required · wire to the dashboard cohort filter
--   from_date, to_date  Date · Required
--   campaign_nm, country_cd, ad_nm  Text · Optional · LEAVE DEFAULT BOXES EMPTY
--   traffic      Text · Optional · leave EMPTY to match the master TOTAL.
--                Set to  Paid%  for a paid-only view.
--   synced_only  Text · Optional · leave EMPTY to match the master TOTAL.
--                Set to  Y  to drop days where Facebook spend has not loaded.
--
-- Tile -> first column in the SELECT (a Number card shows only column 1):
--   Spend spend | CPL cpl | Contacts contacts_registered | Demo Booked demos_booked
--   Attendance % att_pct | Conversion % conversion_pct | ROAS roas_first_time
--   ARPU arpu
--
-- PASTE CHECK: last line ends  [[AND {{synced_only}} = 'Y']];  and the file
-- contains att_pct. If not, the paste truncated.

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
      AND csb.created_at <  DATE_ADD(CURDATE(), INTERVAL 1 DAY)
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
      AND cs.class_date <  DATE_ADD(CURDATE(), INTERVAL 1 DAY)
),

book_attr AS (
    SELECT cl.capture_date, cl.source_campaign, cl.ad_key,
           bp.booking_id, bp.is_cancelled, bp.attended_class, bp.class_date,
           1 AS by_id
    FROM book_pool bp
    JOIN cohort_leads cl
           ON cl.lead_key = bp.leads_contact_utm_id
          AND bp.booked_date BETWEEN cl.capture_date AND cl.window_end
    UNION ALL
    SELECT lbp.capture_date, lbp.source_campaign, lbp.ad_key,
           bp.booking_id, bp.is_cancelled, bp.attended_class, bp.class_date,
           0 AS by_id
    FROM book_pool bp
    LEFT JOIN cohort_leads c2 ON c2.lead_key = bp.leads_contact_utm_id
    JOIN lead_by_parent lbp
           ON lbp.parent_id = bp.parent_id
          AND bp.booked_date BETWEEN lbp.capture_date AND lbp.window_end
    WHERE c2.lead_key IS NULL          -- anti-join: unstamped, or stamped at a
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

prior AS (
    SELECT i.parent_id, MIN(DATE(i.created_at)) AS first_invoice
    FROM invoices i
    JOIN scoped_parents sp ON sp.parent_id = i.parent_id
    WHERE i.invoice_type = 'regular'
    GROUP BY 1
),

attended_pool AS (
    SELECT DISTINCT csb.parent_id, DATE(cs.class_date) AS attended_date
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
                   AND DATE(i.created_at) BETWEEN lbp.capture_date AND lbp.window_end
    LEFT JOIN currencies curr ON i.currency = curr.currency
    LEFT JOIN prior pr ON pr.parent_id = i.parent_id
                      AND pr.first_invoice < lbp.capture_date
    WHERE i.type_of_booking IN ('New','Token','Repeat')
    GROUP BY 1,2,3
),

conv_after_demo AS (
    SELECT lbp.capture_date, lbp.source_campaign, lbp.ad_key,
           COUNT(DISTINCT i.parent_id) AS conversions_after_demo
    FROM lead_by_parent lbp
    JOIN invoices i ON i.parent_id = lbp.parent_id
                   AND DATE(i.created_at) BETWEEN lbp.capture_date AND lbp.window_end
    LEFT JOIN prior pr ON pr.parent_id = i.parent_id
                      AND pr.first_invoice < lbp.capture_date
    JOIN attended_pool ap ON ap.parent_id = lbp.parent_id
                         AND ap.attended_date BETWEEN lbp.capture_date AND lbp.window_end
    WHERE i.type_of_booking IN ('New','Token')
      AND i.invoice_type = 'regular'
      AND pr.parent_id IS NULL
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
        COALESCE(cad.conversions_after_demo,0)        AS conversions_after_demo,
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
    LEFT JOIN conv_after_demo cad
           ON cad.capture_date = lc.capture_date
          AND cad.source_campaign = lc.source_campaign
          AND cad.ad_key <=> lc.ad_key
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
    ROUND(SUM(d.spend))                                              AS spend,
    ROUND(SUM(d.spend) / NULLIF(SUM(d.contacts_registered),0))       AS cpl,
    SUM(d.contacts_registered)                                       AS contacts_registered,

    SUM(d.demos_booked)                                              AS demos_booked,
    SUM(d.demos_booked_held)                                         AS demos_booked_held,
    SUM(d.demos_booked_attended)                                     AS demos_attended,
    ROUND(100 * SUM(d.demos_booked_attended)
              / NULLIF(SUM(d.demos_booked),0), 1)                    AS att_pct,
    ROUND(100 * SUM(d.demos_booked_attended)
              / NULLIF(SUM(d.demos_booked_held),0), 1)               AS att_pct_of_held,
    SUM(d.demos_scheduled)                                           AS demos_scheduled,
    ROUND(100 * SUM(d.demos_attended)
              / NULLIF(SUM(d.demos_scheduled),0), 1)                 AS show_up_rate_pct,

    SUM(d.conversions_first_time)                                    AS conversions,
    SUM(d.conversions_incl_existing)                                 AS conversions_incl_existing,
    SUM(d.conversions_after_demo)                                    AS conversions_after_demo,
    ROUND(100 * SUM(d.conversions_first_time)
              / NULLIF(SUM(d.demos_attended),0), 1)                  AS conversion_pct,
    ROUND(100 * SUM(d.conversions_after_demo)
              / NULLIF(SUM(d.demos_booked_attended),0), 1)           AS demo_to_customer_pct,
    ROUND(100 * SUM(d.conversions_first_time)
              / NULLIF(SUM(d.contacts_registered),0), 2)             AS lead_to_customer_pct,

    SUM(d.new_units)                                                 AS new_units,
    ROUND(SUM(d.new_revenue_first_time)
              / NULLIF(SUM(d.conversions_first_time),0))             AS arpu,
    ROUND(SUM(d.new_revenue) / NULLIF(SUM(d.new_units),0))           AS aov,
    ROUND(SUM(d.new_revenue))                                        AS new_revenue,
    ROUND(SUM(d.new_revenue_first_time))                             AS new_revenue_first_time,
    ROUND(SUM(d.new_revenue_first_time) / NULLIF(SUM(d.spend),0), 2) AS roas_first_time,
    ROUND(SUM(d.new_revenue) / NULLIF(SUM(d.spend),0), 2)            AS new_revenue_roas,
    ROUND((SUM(d.new_revenue) + SUM(d.repeat_revenue))
              / NULLIF(SUM(d.spend),0), 2)                           AS total_roas,

    SUM(d.impressions)                                               AS impressions,
    SUM(d.clicks)                                                    AS clicks,
    ROUND(100 * SUM(d.clicks) / NULLIF(SUM(d.impressions),0), 2)     AS ctr,
    SUM(d.fb_results)                                                AS fb_results
FROM detail d
WHERE 1=1
  [[AND d.campaign_name IN ({{campaign_nm}})]]
  [[AND d.ad_name       = {{ad_nm}}]]
  [[AND d.country_code  = {{country_cd}}]]
  [[AND d.traffic_type LIKE {{traffic}}]]
  [[AND d.d1 <= (SELECT MAX(DATE(a.capture_date)) FROM facebookads a)
    AND {{synced_only}} = 'Y']];
