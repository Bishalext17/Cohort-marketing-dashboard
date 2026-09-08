-- ============================================================================
-- 32_ios_android_device_comparison.sql
-- Device Audit via os_family_code: Evaluates iOS vs Android Funnel Breakdown
-- Key Finding: iOS converts ~2.6x higher; the gap opens at Attendance, not Booking.
-- ============================================================================

SELECT 
    CASE 
        WHEN LOWER(l.os_family_code) LIKE '%ios%' OR LOWER(l.os_family_code) LIKE '%iphone%' OR LOWER(l.os_family_code) LIKE '%ipad%' THEN 'iOS'
        WHEN LOWER(l.os_family_code) LIKE '%android%' THEN 'Android'
        ELSE 'Desktop/Other'
    END AS device_os,
    COUNT(DISTINCT l.lead_id) AS leads_count,
    ROUND(COUNT(DISTINCT l.lead_id) * 100.0 / SUM(COUNT(DISTINCT l.lead_id)) OVER(), 1) AS leads_share_pct,
    COUNT(DISTINCT CASE WHEN l.booked_day_offset >= 0 THEN l.lead_id END) AS booked_count,
    ROUND(COUNT(DISTINCT CASE WHEN l.booked_day_offset >= 0 THEN l.lead_id END) * 100.0 / COUNT(DISTINCT l.lead_id), 1) AS booking_pct,
    COUNT(DISTINCT CASE WHEN l.attended_day_offset >= 0 THEN l.lead_id END) AS attended_count,
    ROUND(COUNT(DISTINCT CASE WHEN l.attended_day_offset >= 0 THEN l.lead_id END) * 100.0 / COUNT(DISTINCT l.lead_id), 1) AS attendance_pct,
    COUNT(DISTINCT CASE WHEN l.converted_day_offset >= 0 THEN l.lead_id END) AS conversions_count,
    ROUND(COUNT(DISTINCT CASE WHEN l.converted_day_offset >= 0 THEN l.lead_id END) * 100.0 / COUNT(DISTINCT l.lead_id), 2) AS conversion_pct,
    SUM(CASE WHEN l.converted_day_offset >= 0 THEN l.revenue ELSE 0 END) AS total_revenue,
    ROUND(SUM(CASE WHEN l.converted_day_offset >= 0 THEN l.revenue ELSE 0 END) / NULLIF(COUNT(DISTINCT CASE WHEN l.converted_day_offset >= 0 THEN l.lead_id END), 0), 2) AS arpu
FROM fact_lead_conversions l
WHERE l.capture_date BETWEEN '2026-08-01' AND '2026-08-31'
  AND l.traffic_type LIKE 'Paid%'
GROUP BY 1
ORDER BY leads_count DESC;
