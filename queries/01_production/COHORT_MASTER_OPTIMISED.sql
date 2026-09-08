-- ============================================================================
-- COHORT_MASTER_OPTIMISED.sql
-- The Master Card and Definition of Truth for Cohort Marketing Performance
-- Rules Enforced:
-- 1. Fixed at D0: spend, impressions, clicks, contacts_registered, ctr, cpl
-- 2. Cohort-dependent: demos booked/scheduled/attended, conversions, new revenue, arpu, roas
-- 3. Maturity Gate: capture_date + offset <= refresh_date
-- 4. Traffic Type: Paid% filter applied
-- ============================================================================

WITH mature_dates AS (
    -- Maturity Gate CTE: Only include dates whose cohort window has fully elapsed
    SELECT DISTINCT capture_date
    FROM dim_calendar
    WHERE capture_date BETWEEN {{date_from}} AND {{date_to}}
      AND ({{cohort_period}} = 'Till date' OR DATE_ADD(capture_date, INTERVAL {{cohort_offset_days}} DAY) <= {{refresh_timestamp}})
),

spend_d0 AS (
    -- Acquisition Day Facts (Fixed at D0 Grain: date, campaign, adset, ad)
    SELECT 
        s.ad_date AS capture_date,
        s.campaign_id,
        s.campaign_name,
        s.adset_id,
        s.adset_name,
        s.ad_id,
        s.ad_name,
        s.channel,
        s.platform,
        s.country,
        COALESCE(s.course_tag, 'Others') AS course,
        SUM(s.spend) AS spend,
        SUM(s.impressions) AS impressions,
        SUM(s.clicks) AS clicks,
        SUM(s.contacts_registered) AS contacts_registered
    FROM fact_marketing_spend s
    JOIN mature_dates m ON s.ad_date = m.capture_date
    WHERE s.traffic_type LIKE 'Paid%'
      AND s.data_status = 'Complete'
      [[AND s.channel IN ({{channel}})]]
      [[AND s.country IN ({{country}})]]
      [[AND s.platform IN ({{platform}})]]
      [[AND s.course_tag IN ({{course}})]]
      [[AND s.campaign_id IN ({{campaign_id}})]]
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
),

lead_events AS (
    -- Lead Grain with Cumulative Offset Evaluation
    SELECT 
        l.capture_date,
        l.campaign_id,
        l.adset_id,
        l.ad_id,
        COUNT(DISTINCT l.lead_id) AS leads_count,
        COUNT(DISTINCT CASE 
            WHEN l.booked_day_offset >= 0 
             AND ({{cohort_period}} = 'Till date' OR l.booked_day_offset <= {{cohort_offset_days}})
            THEN l.lead_id END) AS demos_booked,
        COUNT(DISTINCT CASE 
            WHEN l.scheduled_day_offset >= 0 
             AND ({{cohort_period}} = 'Till date' OR l.scheduled_day_offset <= {{cohort_offset_days}})
            THEN l.lead_id END) AS demos_scheduled,
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
    GROUP BY 1, 2, 3, 4
)

SELECT 
    sp.capture_date,
    sp.channel,
    sp.country,
    sp.platform,
    sp.course,
    sp.campaign_id,
    sp.campaign_name,
    sp.adset_id,
    sp.adset_name,
    sp.ad_id,
    sp.ad_name,
    -- D0 Acquisition Metrics
    sp.spend,
    sp.impressions,
    sp.clicks,
    sp.contacts_registered,
    ROUND(sp.clicks / NULLIF(sp.impressions, 0) * 100, 2) AS ctr_pct,
    ROUND(sp.spend / NULLIF(sp.contacts_registered, 0), 2) AS cpl,
    -- Cohort Cumulative Progression Metrics
    COALESCE(le.demos_booked, 0) AS demos_booked,
    COALESCE(le.demos_scheduled, 0) AS demos_scheduled,
    COALESCE(le.demos_attended, 0) AS demos_attended,
    ROUND(COALESCE(le.demos_attended, 0) / NULLIF(sp.contacts_registered, 0) * 100, 2) AS attendance_pct,
    COALESCE(le.conversions, 0) AS conversions,
    ROUND(COALESCE(le.conversions, 0) / NULLIF(sp.contacts_registered, 0) * 100, 2) AS conversion_pct,
    COALESCE(le.new_revenue, 0) AS new_revenue,
    ROUND(COALESCE(le.new_revenue, 0) / NULLIF(le.conversions, 0), 2) AS arpu,
    ROUND(COALESCE(le.new_revenue, 0) / NULLIF(sp.spend, 0), 2) AS roas
FROM spend_d0 sp
LEFT JOIN lead_events le 
  ON sp.capture_date = le.capture_date
 AND sp.campaign_id = le.campaign_id
 AND sp.adset_id = le.adset_id
 AND sp.ad_id = le.ad_id
ORDER BY sp.capture_date DESC, sp.spend DESC;
