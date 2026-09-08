-- ============================================================================
-- 24_kpi_unified.sql
-- All Eight KPI Tiles from One Query (Matches Master TOTAL Row Exactly)
-- ============================================================================

WITH mature_dates AS (
    SELECT DISTINCT capture_date
    FROM dim_calendar
    WHERE capture_date BETWEEN {{date_from}} AND {{date_to}}
      AND ({{cohort_period}} = 'Till date' OR DATE_ADD(capture_date, INTERVAL {{cohort_offset_days}} DAY) <= {{refresh_timestamp}})
),

tot_spend AS (
    SELECT 
        SUM(spend) AS total_spend,
        SUM(impressions) AS total_impressions,
        SUM(clicks) AS total_clicks,
        SUM(contacts_registered) AS total_leads
    FROM fact_marketing_spend s
    JOIN mature_dates m ON s.ad_date = m.capture_date
    WHERE s.traffic_type LIKE 'Paid%'
      AND s.data_status = 'Complete'
      [[AND s.channel IN ({{channel}})]]
      [[AND s.country IN ({{country}})]]
      [[AND s.platform IN ({{platform}})]]
      [[AND s.course_tag IN ({{course}})]]
      [[AND s.campaign_id IN ({{campaign_id}})]]
),

tot_cohort AS (
    SELECT 
        COUNT(DISTINCT CASE 
            WHEN l.attended_day_offset >= 0 
             AND ({{cohort_period}} = 'Till date' OR l.attended_day_offset <= {{cohort_offset_days}})
            THEN l.lead_id END) AS total_attended,
        COUNT(DISTINCT CASE 
            WHEN l.converted_day_offset >= 0 
             AND ({{cohort_period}} = 'Till date' OR l.converted_day_offset <= {{cohort_offset_days}})
            THEN l.lead_id END) AS total_conversions,
        SUM(CASE 
            WHEN l.converted_day_offset >= 0 
             AND ({{cohort_period}} = 'Till date' OR l.converted_day_offset <= {{cohort_offset_days}})
            THEN l.revenue ELSE 0 END) AS total_revenue
    FROM fact_lead_conversions l
    JOIN mature_dates m ON l.capture_date = m.capture_date
    WHERE l.traffic_type LIKE 'Paid%'
)

SELECT 
    ts.total_spend AS spend,
    ts.total_leads AS contacts_registered,
    ROUND(ts.total_spend / NULLIF(ts.total_leads, 0), 2) AS cpl,
    tc.total_attended AS demos_attended,
    ROUND(tc.total_attended / NULLIF(ts.total_leads, 0) * 100, 2) AS attendance_pct,
    tc.total_conversions AS conversions,
    ROUND(tc.total_conversions / NULLIF(ts.total_leads, 0) * 100, 2) AS conversion_pct,
    tc.total_revenue AS new_revenue,
    ROUND(tc.total_revenue / NULLIF(tc.total_conversions, 0), 2) AS arpu,
    ROUND(tc.total_revenue / NULLIF(ts.total_spend, 0), 2) AS roas,
    ROUND(ts.total_clicks / NULLIF(ts.total_impressions, 0) * 100, 2) AS ctr_pct
FROM tot_spend ts
CROSS JOIN tot_cohort tc;
