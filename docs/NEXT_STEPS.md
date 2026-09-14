# Outstanding Work Items & Engineering Action Items

### Priority 1: Attribution & Tracking
1. **Agree Lead Definition**: `[Done]` Event log prioritized for capture-date attribution with fallback to legacy `leads`.
2. **Add `leads_contact_utm_id` to `invoices`**: `[Scripted]` Migration scripted in `queries/01_production/01_apply_composite_indexes.sql` and backfill bridge added in `backend/scripts/sync_cohort_cache.py`.
3. **Fix the Tagging Leak**:
   - `[Done]` `parent.bambinos.live/signup` categorized as `Direct / Organic Web` in `campaign_tagger.py`.
   - `[Done]` Contact lookback reconciliation bridges orphan invoices to prior registered touchpoints.

### Priority 2: Database & Performance
4. **Deploy Indexes**: `[Ready]` Production DDL script ready in `queries/01_production/01_apply_composite_indexes.sql`.
5. **Nightly Pipeline Automation**: `[Done]` Master orchestrator `run_daily_pipeline.py` sequences Meta Ingestion → Cache Sync → Reconciliation Checks → Cache Invalidation.

### Priority 3: Conversion Rate Optimization (CRO)
6. **Investigate Android Attendance Drop**:
   - Both iOS and Android book demos at equal rates (~60%).
   - Android drops significantly at Attendance (25.1% vs 32.9%).
   - Action item: Optimize WhatsApp/SMS calendar sync and direct join links specifically for Android users.

