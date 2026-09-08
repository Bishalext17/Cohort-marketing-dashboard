-- ============================================================================
-- 20_slice_by_optimised.sql
-- Dynamic Slicing by Date / Campaign / Ad / Country / Platform from Dropdown
-- Grouping strictly uses IDs to prevent collision across identical entity names
-- ============================================================================

WITH mature_dates AS (
    SELECT DISTINCT capture_date
    FROM dim_calendar
    WHERE capture_date BETWEEN {{date_from}} AND {{date_to}}
      AND ({{cohort_period}} = 'Till date' OR DATE_ADD(capture_date, INTERVAL {{cohort_offset_days}} DAY) <= {{refresh_timestamp}})
),

base_spend AS (
    SELECT 
        {{slice_dimension_expr}} AS dimension_value,
        SUM(spend) AS spend,
        SUM(impressions) AS impressions,
        SUM(clicks) AS clicks,
        SUM(contacts_registered) AS contacts_registered
    FROM fact_marketing_spend s
    JOIN mature_dates m ON s.ad_date = m.capture_date
    WHERE s.traffic_type LIKE 'Paid%'
      AND s.data_status = 'Complete'
    GROUP BY 1
),

base_cohort AS (
    SELECT 
        {{slice_lead_dimension_expr}} AS dimension_value,
        COUNT(DISTINCT CASE 
            WHEN l.attended_day_offset >= 0 
             AND ({{cohort_period}} = 'Till date' OR l.attended_day_offset <= {{cohort_offset_days}})
            THEN l.lead_id END) AS demos_attended,
        COUNT(DISTINCT CASE 
            WHEN l.converted_day_offset >= 0 
             AND ({{cohort_period}} = 'Till date' OR l.converted_day_offset <= {{cohort_offset_days}})
            THEN l.lead_id END) AS conversions,
        SUM(CASE 
            WHEN l.converted_day_offset >= 0 
             AND ({{cohort_period}} = 'Till date' OR l.converted_day_offset <= {{cohort_offset_days}})
            THEN l.revenue ELSE 0 END) AS new_revenue
    FROM fact_lead_conversions l
    JOIN mature_dates m ON l.capture_date = m.capture_date
    WHERE l.traffic_type LIKE 'Paid%'
    GROUP BY 1
)

SELECT 
    bs.dimension_value,
    bs.spend,
    bs.impressions,
    bs.clicks,
    bs.contacts_registered,
    ROUND(bs.spend / NULLIF(bs.contacts_registered, 0), 2) AS cpl,
    COALESCE(bc.demos_attended, 0) AS demos_attended,
    ROUND(COALESCE(bc.demos_attended, 0) / NULLIF(bs.contacts_registered, 0) * 100, 2) AS attendance_pct,
    COALESCE(bc.conversions, 0) AS conversions,
    ROUND(COALESCE(bc.conversions, 0) / NULLIF(bs.contacts_registered, 0) * 100, 2) AS conversion_pct,
    COALESCE(bc.new_revenue, 0) AS new_revenue,
    ROUND(COALESCE(bc.new_revenue, 0) / NULLIF(bc.conversions, 0), 2) AS arpu,
    ROUND(COALESCE(bc.new_revenue, 0) / NULLIF(bs.spend, 0), 2) AS roas
FROM base_spend bs
LEFT JOIN base_cohort bc ON bs.dimension_value = bc.dimension_value
ORDER BY bs.spend DESC;
