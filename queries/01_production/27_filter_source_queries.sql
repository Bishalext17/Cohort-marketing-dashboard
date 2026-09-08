-- ============================================================
-- 27 · FILTER SOURCE QUERIES (dropdown value lists)
--
-- HOW TO BUILD ONE — work backwards from the predicate it feeds.
--
--   1. Find what the filter is compared against in the dashboard queries.
--      Campaign is compared against TWO expressions:
--          a.campaign_name                                    -- spend side
--          COALESCE(NULLIF(e.utm_campaign,''),'NA')           -- enquiry side
--
--   2. Reproduce those expressions EXACTLY in the list query. Not the raw
--      column — the whole expression. If the dashboard wraps a column in
--      COALESCE/NULLIF, the list must too, or it will offer values the
--      predicate cannot match. No error, just an empty table.
--
--   3. UNION the sides. A campaign with enquiries but no spend rows exists on
--      one side only. Take it from just the spend table and it vanishes from
--      the dropdown, and someone concludes the campaign is missing.
--
--   4. Bound it by recency. Without a date floor the list grows for ever and
--      the dropdown fills with campaigns that stopped running last year.
--
--   5. Return ONE column. Metabase uses a single column as the value source.
-- ============================================================


-- ============================================================
-- CAMPAIGN — save as "Campaign list (filter source)"
-- Value column in Metabase: campaign_name
-- ============================================================
SELECT DISTINCT campaign_name
FROM (
    SELECT campaign_name
    FROM facebookads
    WHERE capture_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
    UNION
    SELECT COALESCE(NULLIF(utm_campaign,''),'NA')
    FROM leads_contact_event_logs
    WHERE deleted_at IS NULL
      AND event_type = 'contact_submitted'
      AND created_at >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
) t
WHERE campaign_name IS NOT NULL AND campaign_name <> ''
ORDER BY campaign_name;


-- ============================================================
-- COUNTRY — save as "Country list (filter source)"
-- Value column: country_code
-- ============================================================
SELECT DISTINCT country_code
FROM ( SELECT campaign_code, MIN(country_code) AS country_code
       FROM onlinecampaigns GROUP BY campaign_code ) b
WHERE country_code IS NOT NULL AND country_code <> ''
ORDER BY country_code;


-- ============================================================
-- AD NAME — save as "Ad list (filter source)"
-- Value column: ad_name
-- ============================================================
SELECT DISTINCT COALESCE(ad_name,'Not Available') AS ad_name
FROM facebookads
WHERE capture_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
ORDER BY ad_name;


-- ============================================================
-- AD SET — save as "Ad set list (filter source)"
-- Value column: adset_name   (Ad set & ad spend tab only)
-- ============================================================
SELECT DISTINCT COALESCE(adset_name,'Not Available') AS adset_name
FROM facebookads
WHERE capture_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
ORDER BY adset_name;
