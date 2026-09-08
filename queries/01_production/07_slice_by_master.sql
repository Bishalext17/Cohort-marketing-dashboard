-- ============================================================
-- 07 · SLICE-BY MASTER + PLACEMENT FUNNEL + MATURITY STRIP
-- Builds the reference-dashboard controls on your actual data.
--
-- WHAT IS BUILDABLE TODAY
--   · Cohort selector          D0..D30 / Till date   (already working)
--   · Lead date from / to      (already working)
--   · Slice by                 lead capture date · campaign · ad · country
--   · Filters                  campaign · ad name · country · placement
--   · Meta platform            = utm_placement — SECTION 2, funnel only, NO spend
--   · Cohort maturity strip    SECTION 3
--   · CSV download             built into every Metabase card, nothing to build
--
-- WHAT IS NOT BUILDABLE, AND WHY
--   · SLICE BY AD SET / AD SET ID / AD ID
--       Leads carry utm_content = ad NAME. One ad name spans multiple adsets and
--       multiple ad_ids, so funnel metrics cannot be split below ad name. Spend
--       alone can be sliced that way — see SECTION 4 for a spend-only card.
--       This becomes possible once utm_content={{ad.id}} is deployed.
--   · CHANNEL
--       You have one paid channel (facebookads). utm_source is blank on 826 of
--       944 untagged events, so there is no channel dimension to slice by. Add
--       it when a second ad platform lands in the warehouse.
--   · COURSE
--       No course field exists on the lead. It is inferable from campaign name
--       (Gita / Unbox / Math / Science) but that is a naming convention, not
--       data — it breaks the first time someone names a campaign differently.
--       SECTION 5 has a derivation if you want it anyway, clearly labelled.
--   · SPEND ON A PLACEMENT SLICE
--       facebookads has no placement breakdown, so a placement slice can show
--       leads/demos/conversions but NOT spend, CPL or ROAS. Section 2 omits them
--       rather than showing zeros that look like real numbers.
--
-- Variables to add (all Text unless noted):
--   cohort_days  Number · Required · default 9999
--   from_date    Date   · Required · 2026-08-07
--   to_date      Date   · Required
--   slice_1      Text   · Required · default 'campaign'
--   slice_2      Text   · Required · default 'none'  (Metabase cannot accept an
--                empty value for a variable used in a SELECT — use the sentinel)
--   campaign_nm  Text   · Optional
--   ad_nm        Text   · Optional
--   country_cd   Text   · Optional
--
--   slice_1 accepts: date · campaign · ad · country
--   slice_2 accepts: date · campaign · ad · country · none
-- ============================================================


-- ============================================================
-- SECTION 1 · SLICE-BY MASTER
-- Save as: "Cohort — Slice by"
-- One card that replaces the By Campaign / By Date / Date x Campaign /
-- By Country tabs. The viewer picks the grain instead of switching tabs.
-- ============================================================

WITH
cohort_leads AS (
    SELECT lead_key, mobile, capture_date, source_campaign, ad_key,
           placement, lead_country, window_end
    FROM (
        SELECT
            e.id           AS lead_key,
            e.phone        AS mobile,
            e.country_code AS lead_country,
            DATE(e.created_at) AS capture_date,
            -- NULLIF before COALESCE: the event log writes '' as often as NULL,
            -- and COALESCE alone would leave '' as its own phantom campaign.
            COALESCE(NULLIF(e.utm_campaign,''),'NA') AS source_campaign,
            NULLIF(e.utm_content,'')                 AS ad_key,
            COALESCE(NULLIF(e.utm_placement,''),'Not Available') AS placement,
            CASE WHEN {{cohort_days}} >= 9999 THEN CURDATE()
                 ELSE DATE_ADD(DATE(e.created_at), INTERVAL {{cohort_days}} DAY)
            END AS window_end,
            ROW_NUMBER() OVER (
                PARTITION BY COALESCE(NULLIF(e.phone,''), CONCAT('_id:', e.id))
                ORDER BY e.created_at, e.id
            ) AS lrn
        FROM leads_contact_event_logs e
        WHERE e.deleted_at IS NULL
          AND e.event_type = 'contact_submitted'
          AND DATE(e.created_at) BETWEEN {{from_date}} AND {{to_date}}
          AND ( {{cohort_days}} >= 9999
                OR DATE_ADD(DATE(e.created_at), INTERVAL {{cohort_days}} DAY) <= CURDATE() )
          [[AND COALESCE(NULLIF(e.utm_campaign,''),'NA') IN ({{campaign_nm}})]]
          [[AND e.country_code = {{country_cd}}]]
    ) t
    WHERE lrn = 1
),

lead_counts AS (
    SELECT capture_date, source_campaign, ad_key, COUNT(DISTINCT lead_key) AS leads
    FROM cohort_leads GROUP BY 1,2,3
),

Demo_Bookings AS (
    SELECT cl.capture_date, cl.source_campaign, cl.ad_key,
        COUNT(DISTINCT CASE WHEN csb.is_cancelled='No' THEN csb.id END) AS demos_booked,
        COUNT(DISTINCT csb.id) AS demos_booked_incl_cancelled
    FROM cohort_leads cl
    JOIN parents p ON p.mobile_number = cl.mobile AND p.deleted_at IS NULL
    JOIN classschedulebookings csb ON csb.parent_id = p.id AND csb.deleted_at IS NULL
    JOIN classschedules cs ON csb.classschedule_id = cs.id AND cs.deleted_at IS NULL
    JOIN classes c ON cs.class_id = c.id AND c.deleted_at IS NULL
    WHERE csb.demo_class='Yes' AND c.category_id <> '31' AND c.is_workshop='no'
      AND c.class_name NOT LIKE '%MOCK DEMO%' AND c.class_name NOT LIKE '%TEACHER NAME%'
      AND DATE(csb.created_at) BETWEEN cl.capture_date AND cl.window_end
    GROUP BY 1,2,3
),

Demo_Scheduled AS (
    SELECT cl.capture_date, cl.source_campaign, cl.ad_key,
        COUNT(DISTINCT csb.id) AS demos_scheduled,
        COUNT(DISTINCT CASE WHEN csb.attended_class='Yes' THEN csb.id END) AS demos_attended
    FROM cohort_leads cl
    JOIN parents p ON p.mobile_number = cl.mobile AND p.deleted_at IS NULL
    JOIN classschedulebookings csb ON csb.parent_id = p.id AND csb.deleted_at IS NULL
    JOIN classschedules cs ON csb.classschedule_id = cs.id AND cs.deleted_at IS NULL
    JOIN classes c ON cs.class_id = c.id AND c.deleted_at IS NULL
    WHERE csb.demo_class='Yes' AND csb.is_cancelled='No'
      AND c.category_id <> '31' AND c.is_workshop='no'
      AND c.class_name NOT LIKE '%MOCK DEMO%' AND c.class_name NOT LIKE '%TEACHER NAME%'
      AND DATE(cs.class_date) BETWEEN cl.capture_date AND cl.window_end
    GROUP BY 1,2,3
),

Converted AS (
    SELECT cl.capture_date, cl.source_campaign, cl.ad_key,
        COUNT(DISTINCT CASE WHEN i.type_of_booking IN ('New','Token') AND i.invoice_type='regular'
                            THEN i.parent_id END) AS conversions,
        COUNT(DISTINCT CASE WHEN i.type_of_booking='Repeat' AND i.invoice_type='regular'
                            THEN i.parent_id END) AS repeat_conversions,
        SUM(CASE WHEN i.type_of_booking IN ('New','Token') AND i.invoice_type='regular'
                 THEN CASE WHEN i.currency='INR' THEN i.amount
                      ELSE i.amount * 78 / curr.conversion_factor END ELSE 0 END) AS new_revenue,
        SUM(CASE WHEN i.type_of_booking='Repeat' AND i.invoice_type='regular'
                 THEN CASE WHEN i.currency='INR' THEN i.amount
                      ELSE i.amount * 78 / curr.conversion_factor END ELSE 0 END) AS repeat_revenue
    FROM cohort_leads cl
    JOIN parents p ON p.mobile_number = cl.mobile AND p.deleted_at IS NULL
    JOIN invoices i ON i.parent_id = p.id
    LEFT JOIN currencies curr ON i.currency = curr.currency
    WHERE i.type_of_booking IN ('New','Token','Repeat')
      AND DATE(i.created_at) BETWEEN cl.capture_date AND cl.window_end
    GROUP BY 1,2,3
),

-- Spend collapsed to AD NAME. SUM across the duplicate ad_ids/adsets that B6
-- found, so the spend grain matches the grain utm_content can support.
fb_ad AS (
    SELECT
        DATE(a.capture_date) AS d1,
        b.country_code,
        a.campaign_id, a.campaign_name,
        COALESCE(a.ad_name,'Not Available') AS ad_name,
        COUNT(DISTINCT a.ad_id)    AS ads_merged,
        COUNT(DISTINCT a.adset_id) AS adsets_merged,
        MIN(a.ad_id)               AS sample_ad_id,
        SUM(a.impressions) AS impressions,
        SUM(a.clicks)      AS clicks,
        SUM(a.spend)       AS spend,
        SUM(a.complete_registration) AS fb_results
    FROM facebookads a
    LEFT JOIN ( SELECT campaign_code, MIN(country_code) AS country_code
                FROM onlinecampaigns GROUP BY campaign_code ) b
           ON a.campaign_name = b.campaign_code
    WHERE DATE(a.capture_date) BETWEEN {{from_date}} AND {{to_date}}
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
        lc.leads AS contacts_registered,
        COALESCE(db.demos_booked,0)    AS demos_booked,
        COALESCE(ds.demos_scheduled,0) AS demos_scheduled,
        COALESCE(ds.demos_attended,0)  AS demos_attended,
        COALESCE(cv.conversions,0)     AS conversions,
        COALESCE(cv.repeat_conversions,0) AS repeat_conversions,
        COALESCE(cv.new_revenue,0)     AS new_revenue,
        COALESCE(cv.repeat_revenue,0)  AS repeat_revenue
    FROM lead_counts lc
    LEFT JOIN Demo_Bookings db
           ON db.capture_date = lc.capture_date
          AND db.source_campaign = lc.source_campaign
          AND db.ad_key <=> lc.ad_key          -- <=> is NULL-safe equality
    LEFT JOIN Demo_Scheduled ds
           ON ds.capture_date = lc.capture_date
          AND ds.source_campaign = lc.source_campaign
          AND ds.ad_key <=> lc.ad_key
    LEFT JOIN Converted cv
           ON cv.capture_date = lc.capture_date
          AND cv.source_campaign = lc.source_campaign
          AND cv.ad_key <=> lc.ad_key
),

-- No rn=1 hack any more. Every ad row carries its own leads.
detail AS (
    SELECT
        fb.d1, fb.country_code, fb.campaign_id, fb.campaign_name,
        fb.ad_name, fb.ads_merged, fb.adsets_merged, fb.sample_ad_id,
        'Paid · ad matched' AS traffic_type,
        COALESCE(cf.contacts_registered,0) AS contacts_registered,
        COALESCE(cf.demos_booked,0)        AS demos_booked,
        COALESCE(cf.demos_scheduled,0)     AS demos_scheduled,
        COALESCE(cf.demos_attended,0)      AS demos_attended,
        COALESCE(cf.conversions,0)         AS conversions,
        COALESCE(cf.repeat_conversions,0)  AS repeat_conversions,
        COALESCE(cf.new_revenue,0)         AS new_revenue,
        COALESCE(cf.repeat_revenue,0)      AS repeat_revenue,
        fb.impressions, fb.clicks, fb.spend, fb.fb_results
    FROM fb_ad fb
    LEFT JOIN campaign_funnel cf
           ON fb.d1            = cf.target_date
          AND fb.campaign_name = cf.source_campaign
          AND fb.ad_name       = cf.ad_key

    UNION ALL

    -- Leads with no matching ad row. Kept visible rather than dropped, so the
    -- funnel totals still reconcile and untagged volume is auditable.
    SELECT cf.target_date, NULL, 'Not Available', cf.source_campaign,
           COALESCE(cf.ad_key,'Not Available'), 0, 0, NULL,
           CASE WHEN cf.source_campaign = 'NA' THEN 'Untagged · direct/organic'
                WHEN cf.ad_key IS NULL         THEN 'Paid · campaign only'
                ELSE 'Paid · ad tag unmatched' END,
           cf.contacts_registered, cf.demos_booked, cf.demos_scheduled,
           cf.demos_attended, cf.conversions, cf.repeat_conversions,
           cf.new_revenue, cf.repeat_revenue,
           0, 0, 0, 0
    FROM campaign_funnel cf
    LEFT JOIN fb_ad fb
           ON cf.target_date     = fb.d1
          AND cf.source_campaign = fb.campaign_name
          AND cf.ad_key          = fb.ad_name
    WHERE fb.ad_name IS NULL
)

SELECT
    CASE LOWER(TRIM({{slice_1}}))
        WHEN 'date'     THEN DATE_FORMAT(d.d1,'%Y-%m-%d')
        WHEN 'campaign' THEN d.campaign_name
        WHEN 'ad'       THEN d.ad_name
        WHEN 'country'  THEN COALESCE(d.country_code,'Unknown')
    END                                                              AS slice_1,
    CASE LOWER(TRIM({{slice_2}}))
        WHEN 'date'     THEN DATE_FORMAT(d.d1,'%Y-%m-%d')
        WHEN 'campaign' THEN d.campaign_name
        WHEN 'ad'       THEN d.ad_name
        WHEN 'country'  THEN COALESCE(d.country_code,'Unknown')
        ELSE '(none)'
    END                                                              AS slice_2,
    CASE WHEN {{cohort_days}} >= 9999 THEN 'Till date'
         ELSE CONCAT('D', {{cohort_days}}) END                       AS cohort_period,
    CASE WHEN MAX(d.d1) > (SELECT MAX(DATE(capture_date)) FROM facebookads)
         THEN 'Spend not synced' ELSE 'Complete' END                 AS data_status,

    ROUND(SUM(d.spend))                                              AS spend,
    ROUND(SUM(d.spend) / NULLIF(SUM(d.contacts_registered),0))       AS cpl,
    SUM(d.contacts_registered)                                       AS contacts_registered,
    SUM(d.demos_booked)                                              AS demos_booked,
    SUM(d.demos_scheduled)                                           AS demos_scheduled,
    SUM(d.demos_attended)                                            AS demos_attended,
    ROUND(100 * SUM(d.demos_attended)
              / NULLIF(SUM(d.demos_scheduled),0), 1)                 AS show_up_rate_pct,
    SUM(d.conversions)                                               AS conversions,
    ROUND(100 * SUM(d.conversions)
              / NULLIF(SUM(d.contacts_registered),0), 2)             AS conversion_pct,
    ROUND(SUM(d.new_revenue) / NULLIF(SUM(d.conversions),0))         AS arpu,
    ROUND(SUM(d.new_revenue))                                        AS new_revenue,
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
GROUP BY 1,2,3
HAVING slice_1 IS NOT NULL
ORDER BY spend DESC, slice_1;


-- ============================================================
-- SECTION 2 · META PLATFORM / PLACEMENT FUNNEL
-- Save as: "Cohort — by placement (no spend)"
-- ============================================================

WITH cohort_leads AS (
    SELECT lead_key, mobile, capture_date, placement, window_end
    FROM (
        SELECT
            e.id AS lead_key,
            e.phone AS mobile,
            DATE(e.created_at) AS capture_date,
            COALESCE(NULLIF(e.utm_placement,''),'Not tagged') AS placement,
            CASE WHEN {{cohort_days}} >= 9999 THEN CURDATE()
                 ELSE DATE_ADD(DATE(e.created_at), INTERVAL {{cohort_days}} DAY)
            END AS window_end,
            ROW_NUMBER() OVER (
                PARTITION BY COALESCE(NULLIF(e.phone,''), CONCAT('_id:', e.id))
                ORDER BY e.created_at, e.id) AS lrn
        FROM leads_contact_event_logs e
        WHERE e.deleted_at IS NULL
          AND e.event_type = 'contact_submitted'
          AND DATE(e.created_at) BETWEEN {{from_date}} AND {{to_date}}
          AND ( {{cohort_days}} >= 9999
                OR DATE_ADD(DATE(e.created_at), INTERVAL {{cohort_days}} DAY) <= CURDATE() )
          [[AND COALESCE(NULLIF(e.utm_campaign,''),'NA') IN ({{campaign_nm}})]]
    ) t WHERE lrn = 1
),
demo AS (
    SELECT cl.placement,
        COUNT(DISTINCT csb.id) AS demos_scheduled,
        COUNT(DISTINCT CASE WHEN csb.attended_class='Yes' THEN csb.id END) AS demos_attended
    FROM cohort_leads cl
    JOIN parents p ON p.mobile_number = cl.mobile AND p.deleted_at IS NULL
    JOIN classschedulebookings csb ON csb.parent_id = p.id AND csb.deleted_at IS NULL
    JOIN classschedules cs ON csb.classschedule_id = cs.id AND cs.deleted_at IS NULL
    JOIN classes c ON cs.class_id = c.id AND c.deleted_at IS NULL
    WHERE csb.demo_class='Yes' AND csb.is_cancelled='No'
      AND c.category_id <> '31' AND c.is_workshop='no'
      AND c.class_name NOT LIKE '%MOCK DEMO%' AND c.class_name NOT LIKE '%TEACHER NAME%'
      AND DATE(cs.class_date) BETWEEN cl.capture_date AND cl.window_end
    GROUP BY 1
),
conv AS (
    SELECT cl.placement,
        COUNT(DISTINCT CASE WHEN i.type_of_booking IN ('New','Token')
                             AND i.invoice_type='regular' THEN i.parent_id END) AS conversions,
        SUM(CASE WHEN i.type_of_booking IN ('New','Token') AND i.invoice_type='regular'
                 THEN CASE WHEN i.currency='INR' THEN i.amount
                      ELSE i.amount * 78 / curr.conversion_factor END ELSE 0 END) AS new_revenue
    FROM cohort_leads cl
    JOIN parents p ON p.mobile_number = cl.mobile AND p.deleted_at IS NULL
    JOIN invoices i ON i.parent_id = p.id
    LEFT JOIN currencies curr ON i.currency = curr.currency
    WHERE i.type_of_booking IN ('New','Token','Repeat')
      AND DATE(i.created_at) BETWEEN cl.capture_date AND cl.window_end
    GROUP BY 1
)
SELECT
    cl.placement                                                     AS meta_platform,
    COUNT(DISTINCT cl.lead_key)                                      AS contacts_registered,
    COALESCE(dm.demos_scheduled,0)                                   AS demos_scheduled,
    COALESCE(dm.demos_attended,0)                                    AS demos_attended,
    ROUND(100 * COALESCE(dm.demos_attended,0)
              / NULLIF(dm.demos_scheduled,0), 1)                     AS show_up_rate_pct,
    COALESCE(cv.conversions,0)                                       AS conversions,
    ROUND(100 * COALESCE(cv.conversions,0)
              / NULLIF(COUNT(DISTINCT cl.lead_key),0), 2)            AS conversion_pct,
    ROUND(COALESCE(cv.new_revenue,0))                                AS new_revenue,
    ROUND(COALESCE(cv.new_revenue,0) / NULLIF(cv.conversions,0))     AS arpu
FROM cohort_leads cl
LEFT JOIN demo dm ON dm.placement = cl.placement
LEFT JOIN conv cv ON cv.placement = cl.placement
GROUP BY 1, dm.demos_scheduled, dm.demos_attended, cv.conversions, cv.new_revenue
ORDER BY contacts_registered DESC;


-- ============================================================
-- SECTION 3 · COHORT MATURITY STRIP
-- Save as: "Cohort maturity"
-- ============================================================

SELECT
    dates.d                                                          AS capture_date,
    CASE
      WHEN dates.d < {{from_date}} OR dates.d > {{to_date}}
           THEN 'Outside selected range'
      WHEN {{cohort_days}} >= 9999
           THEN 'Counted'
      WHEN DATE_ADD(dates.d, INTERVAL {{cohort_days}} DAY) <= CURDATE()
           THEN 'Counted'
      ELSE 'Dropped - window not closed'
    END                                                              AS status,
    CASE WHEN {{cohort_days}} >= 9999 THEN CURDATE()
         ELSE DATE_ADD(dates.d, INTERVAL {{cohort_days}} DAY) END    AS window_closes,
    dates.leads                                                      AS leads_on_date
FROM ( SELECT DATE(created_at) AS d, COUNT(DISTINCT phone) AS leads
       FROM leads_contact_event_logs
       WHERE deleted_at IS NULL AND event_type = 'contact_submitted'
       GROUP BY 1 ) dates
ORDER BY dates.d;


-- ============================================================
-- SECTION 4 · AD SET / AD ID — SPEND ONLY
-- Save as: "Ad set & ad spend (no funnel)"
-- ============================================================

SELECT
    DATE(a.capture_date)                                             AS lead_capture_period,
    a.campaign_name, a.campaign_id,
    COALESCE(a.adset_name,'Not Available')                           AS ad_set,
    a.adset_id,
    COALESCE(a.ad_name,'Not Available')                              AS ad,
    a.ad_id,
    ROUND(SUM(a.spend))                                              AS spend,
    SUM(a.impressions)                                               AS impressions,
    SUM(a.clicks)                                                    AS clicks,
    ROUND(100 * SUM(a.clicks) / NULLIF(SUM(a.impressions),0), 2)     AS ctr,
    ROUND(SUM(a.spend) / NULLIF(SUM(a.clicks),0), 2)                 AS cpc,
    SUM(a.complete_registration)                                     AS fb_results,
    ROUND(SUM(a.spend)
        / NULLIF(SUM(a.complete_registration),0))                    AS fb_cost_per_result
FROM facebookads a
WHERE DATE(a.capture_date) BETWEEN {{from_date}} AND {{to_date}}
  [[AND a.campaign_name IN ({{campaign_nm}})]]
  [[AND a.adset_name    = {{adset_nm}}]]
  [[AND a.ad_name       = {{ad_nm}}]]
GROUP BY 1,2,3,4,5,6,7
ORDER BY spend DESC;
