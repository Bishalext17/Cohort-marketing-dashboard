-- COURSES CARD — BUG FIX
--
-- The card currently on the dashboard has the date range HARD-CODED:
--     WHERE DATE(capture_date) BETWEEN '2026-08-07' AND '2026-08-12'
-- so it ignores the dashboard filters entirely. With From/To set to 7 Aug it
-- still shows 1,433,152 of spend — six days' worth — instead of ~292k.
-- It will keep showing 7-12 Aug for ever, silently, as the dashboard moves on.
--
-- Replace with this. Variables: from_date, to_date (Date).

SELECT
    CASE
      WHEN campaign_name LIKE '%Gita%'    THEN 'Gita'
      WHEN campaign_name LIKE '%Unbox%'   THEN 'Unbox'
      WHEN campaign_name LIKE '%Math%'    THEN 'Math'
      WHEN campaign_name LIKE '%Science%' THEN 'Science'
      ELSE 'Unclassified'
    END                                            AS course,
    ROUND(SUM(spend))                              AS spend,
    ROUND(100 * SUM(spend) / SUM(SUM(spend)) OVER (), 1) AS pct_of_spend,
    COUNT(DISTINCT campaign_name)                  AS campaigns
FROM facebookads
WHERE capture_date >= {{from_date}}
  AND capture_date <  DATE_ADD({{to_date}}, INTERVAL 1 DAY)
GROUP BY 1
ORDER BY spend DESC;

-- STILL NOT RECOMMENDED FOR PUBLICATION.
-- Measured on the current data: Unclassified = 313,788 of 1,433,152 = 21.9% of
-- spend across 6 campaigns, and Science returns nothing at all. Course is not a
-- field — it is guessed from campaign naming, so it breaks the first time
-- someone names a campaign differently, and it breaks silently.
--
-- Either remove the card, or retitle it "Course (estimated from campaign name)"
-- and keep pct_of_spend visible so the Unclassified share is impossible to miss.
-- It becomes trustworthy only if campaign naming is enforced, or a real course
-- field is added to the campaign metadata.
