-- COHORT — BY PLACEMENT (no spend) [HYPER-OPTIMISED]
-- Rebuilt: revenue is 'New' only (Token removed), first-payment split,
-- attendance on the booking cohort, blank-phone join fixed, deterministic
-- leads_contact_utm_id attribution with phone fallback.
--
-- NO SPEND / CPL / ROAS — facebookads has no placement breakdown. Rank
-- placements on revenue_per_lead and att_pct instead.
--
-- Variables: cohort_days (Number), from_date, to_date (Date),
--            campaign_nm (Text, optional — LEAVE THE DEFAULT BOX EMPTY)
-- PASTE CHECK: last line ends  ORDER BY contacts_registered DESC;

WITH
cohort_leads AS (
    SELECT lead_key, mobile, capture_date, placement, window_end
    FROM (
        SELECT
            e.id                                                 AS lead_key,
            NULLIF(e.phone,'')                                   AS mobile,
            DATE(e.created_at)                                   AS capture_date,
            COALESCE(NULLIF(e.utm_placement,''),'Not tagged')    AS placement,
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
    ) t
    WHERE lrn = 1
),

lead_by_parent AS (
    SELECT p.id AS parent_id, cl.placement, cl.capture_date, cl.window_end
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
        cl.placement,
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
        lbp.placement,
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

Demo_Bookings AS (
    SELECT placement,
        COUNT(DISTINCT CASE WHEN is_cancelled='No' THEN booking_id END)   AS demos_booked,
        COUNT(DISTINCT CASE WHEN is_cancelled='No' AND attended_class='Yes'
                            THEN booking_id END)                          AS demos_booked_attended,
        COUNT(DISTINCT CASE WHEN is_cancelled='No' AND class_date <= CURDATE()
                            THEN booking_id END)                          AS demos_booked_held
    FROM book_attr
    GROUP BY 1
),

prior AS (
    SELECT i.parent_id, MIN(i.created_at) AS first_invoice_ts
    FROM invoices i
    JOIN scoped_parents sp ON sp.parent_id = i.parent_id
    WHERE i.invoice_type = 'regular'
    GROUP BY 1
),

Converted AS (
    SELECT lbp.placement,
        COUNT(DISTINCT CASE WHEN i.type_of_booking IN ('New','Token')
                             AND i.invoice_type='regular'
                             AND pr.parent_id IS NULL
                            THEN i.parent_id END)                         AS conversions,
        COUNT(DISTINCT CASE WHEN i.type_of_booking IN ('New','Token')
                             AND i.invoice_type='regular'
                            THEN i.parent_id END)                         AS conversions_incl_existing,
        SUM(CASE WHEN i.type_of_booking='New' AND i.invoice_type='regular'
                  AND pr.parent_id IS NULL
                 THEN CASE WHEN i.currency='INR' THEN i.amount
                      ELSE i.amount * 78 / NULLIF(curr.conversion_factor,0) END
                 ELSE 0 END)                                              AS new_revenue_first_time,
        SUM(CASE WHEN i.type_of_booking='New' AND i.invoice_type='regular'
                 THEN CASE WHEN i.currency='INR' THEN i.amount
                      ELSE i.amount * 78 / NULLIF(curr.conversion_factor,0) END
                 ELSE 0 END)                                              AS new_revenue
    FROM lead_by_parent lbp
    JOIN invoices i ON i.parent_id = lbp.parent_id
                   AND i.created_at >= CAST(lbp.capture_date AS DATETIME)
                   AND i.created_at <  DATE_ADD(CAST(lbp.window_end AS DATETIME), INTERVAL 1 DAY)
    LEFT JOIN currencies curr ON i.currency = curr.currency
    LEFT JOIN prior pr ON pr.parent_id = i.parent_id
                      AND pr.first_invoice_ts < CAST(lbp.capture_date AS DATETIME)
    WHERE i.type_of_booking IN ('New','Token')
    GROUP BY 1
),

lead_counts AS (
    SELECT placement, COUNT(DISTINCT lead_key) AS contacts_registered
    FROM cohort_leads GROUP BY 1
)

SELECT
    lc.placement                                                     AS meta_platform,
    CASE WHEN {{cohort_days}} >= 9999 THEN 'Till date'
         ELSE CONCAT('D', {{cohort_days}}) END                       AS cohort_period,
    lc.contacts_registered,
    ROUND(100 * lc.contacts_registered
              / NULLIF(SUM(lc.contacts_registered) OVER (),0), 1)    AS share_of_leads_pct,
    COALESCE(db.demos_booked,0)                                      AS demos_booked,
    COALESCE(db.demos_booked_held,0)                                 AS demos_booked_held,
    COALESCE(db.demos_booked_attended,0)                             AS demos_attended,
    ROUND(100 * COALESCE(db.demos_booked_attended,0)
              / NULLIF(db.demos_booked,0), 1)                        AS att_pct,
    ROUND(100 * COALESCE(db.demos_booked_attended,0)
              / NULLIF(db.demos_booked_held,0), 1)                   AS att_pct_of_held,
    COALESCE(cv.conversions,0)                                       AS conversions,
    ROUND(100 * COALESCE(cv.conversions,0)
              / NULLIF(db.demos_booked_attended,0), 1)               AS conversion_pct,
    ROUND(100 * COALESCE(cv.conversions,0)
              / NULLIF(lc.contacts_registered,0), 2)                 AS lead_to_customer_pct,
    ROUND(COALESCE(cv.new_revenue_first_time,0))                     AS new_revenue_first_time,
    ROUND(COALESCE(cv.new_revenue_first_time,0)
              / NULLIF(cv.conversions,0))                            AS arpu,
    -- rank placements on this: no spend available, so revenue per lead is the
    -- fairest quality signal across placements
    ROUND(COALESCE(cv.new_revenue_first_time,0)
              / NULLIF(lc.contacts_registered,0))                    AS revenue_per_lead
FROM lead_counts lc
LEFT JOIN Demo_Bookings db ON db.placement = lc.placement
LEFT JOIN Converted     cv ON cv.placement = lc.placement
ORDER BY contacts_registered DESC;
