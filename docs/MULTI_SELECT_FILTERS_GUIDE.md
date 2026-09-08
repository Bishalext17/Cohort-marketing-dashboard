# Multi-Select Campaign & Dimension Filter Guide

## 1. Syntax Pattern
All production queries have been updated to support multi-select matching via `IN (...)`:

```sql
-- Campaign Name
[[AND a.campaign_name IN ({{campaign_nm}})]]                            -- Spend side
[[AND COALESCE(NULLIF(e.utm_campaign,''),'NA') IN ({{campaign_nm}})]]   -- Lead side

-- Ad Name
[[AND a.ad_name IN ({{ad_nm}})]]

-- Country Code
[[AND b.country_code IN ({{country_cd}})]]
[[AND e.country_code IN ({{country_cd}})]]
```

---

## 2. Metabase Filter Setup Steps

1. **Set Variable Mode**:
   - In the query editor variable sidebar: set Variable type to **Text** and check **"People can pick multiple values"**.
   - Default widget value: **leave empty**.
2. **Dashboard Filter Wiring**:
   - Dashboard Edit → click the **Campaign** filter.
   - Under Settings: select **"People can pick multiple values"**.
   - Map `campaign_nm` across all cards on all tabs.
3. **Behavior**:
   - **Empty Filter**: The whole `[[ ... ]]` clause is ignored and returns 100% of data.
   - **Specific Selections**: Computes exact totals for the selected subset.
