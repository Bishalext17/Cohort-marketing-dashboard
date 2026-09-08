-- ============================================================
-- 26 · ADDING A CAMPAIGN FILTER TO THE DASHBOARD
--
-- Every query already carries the variable:
--     [[AND COALESCE(NULLIF(e.utm_campaign,''),'NA') IN ({{campaign_nm}})]]   -- lead side
--     [[AND a.campaign_name IN ({{campaign_nm}})]]                            -- spend side
-- So nothing in the SQL needs to change. This is dashboard wiring only.
--
-- The [[ ]] brackets mean: empty = no filter at all. That is why leaving the
-- box blank shows everything rather than nothing.
-- ============================================================


-- ============================================================
-- STEP 1 · CREATE THE VALUE LIST (so the filter is a dropdown, not free text)
-- Save this as a question named "Campaign list".
-- Limited to campaigns with recent spend, so the dropdown stays short and does
-- not fill with campaigns that stopped running months ago.
-- ============================================================

SELECT DISTINCT a.campaign_name
FROM facebookads a
WHERE a.capture_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
  AND a.campaign_name IS NOT NULL
  AND a.campaign_name <> ''
ORDER BY 1;

-- If you also want campaigns that produced enquiries but no spend:
/*
SELECT DISTINCT campaign_name FROM (
    SELECT campaign_name FROM facebookads
     WHERE capture_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
    UNION
    SELECT COALESCE(NULLIF(utm_campaign,''),'NA') FROM leads_contact_event_logs
     WHERE deleted_at IS NULL AND event_type='contact_submitted'
       AND created_at >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
) t
WHERE campaign_name IS NOT NULL AND campaign_name <> ''
ORDER BY 1;
*/


-- ============================================================
-- STEP 2 · ADD THE FILTER IN METABASE
--
--   1. Open the dashboard, click the pencil (Edit).
--   2. Click the filter icon > Text or Category > "Is".
--   3. Label it  Campaign
--   4. Under "How should people filter on this widget", choose Dropdown list,
--      then set the value source to "From another model or question" and pick
--      the "Campaign list" question from Step 1.
--   5. Wire it to every card: with the filter selected, each card shows a
--      dropdown — pick  campaign_nm  on each one.
--   6. Save.
-- ============================================================
