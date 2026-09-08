# 5-Phase Dashboard Optimization & Speed Plan

Each phase includes an explicit benchmark measurement step and a stop gate before progressing.

| Phase | Action | Target Execution Time | Stop Gate Verification |
|---|---|---|---|
| **Phase 1: Composite Indexing** | Add composite indexes on `(ad_date, channel, country)` and `(capture_date, traffic_type)` | 8–12s (down from 25–50s) | Query EXPLAIN shows index lookup without table scans |
| **Phase 2: Eliminate Lead/Spend Cartesian Joins** | Separate CTEs for Spend at `(date, camp, adset, ad)` and Lead events at `(capture_date)` | 4–6s | Row counts match formula validation sheet |
| **Phase 3: Nightly Pre-aggregation Cache** | Run `sp_refresh_cohort_cache` at 03:00 UTC to compute all `Dn` buckets | < 800ms | Cache matches raw CTE output on mature dates |
| **Phase 4: In-Memory / Redis API Layer** | Cache API responses in FastAPI with TTL = 3600s | < 50ms | Real-time filter toggling feels instantaneous |
| **Phase 5: Automated Integrity Check** | Daily cron script asserting `Master TOTAL row == Unified KPI Tile values` | Continuous | Email alert if delta > 0.01% |
