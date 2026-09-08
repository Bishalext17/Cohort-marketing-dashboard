# Outstanding Work Items & Engineering Action Items

### Priority 1: Attribution & Tracking
1. **Agree Lead Definition**: Decide between event log (~21% higher volume) vs legacy `leads` table.
2. **Add `leads_contact_utm_id` to `invoices`**: Ensure sales conversions receive the identical granular UTM attribution that booked demos currently enjoy.
3. **Fix the Tagging Leak**:
   - ~21% of revenue comes from untagged web signups (e.g. `parent.bambinos.live/signup` alone contributed ₹6.35L without UTMs).
   - Resolve 43% revenue records that have no preceding enquiry record.

### Priority 2: Database & Performance
4. **Deploy Indexes**: Apply indexes from `queries/02_audits/19_performance_diagnosis.sql` to production MariaDB.
5. **Enable Nightly Stored Procedure**: Schedule `sp_refresh_cohort_cache` nightly at 03:00 IST.

### Priority 3: Conversion Rate Optimization (CRO)
6. **Investigate Android Attendance Drop**:
   - Both iOS and Android book demos at equal rates (~60%).
   - Android drops significantly at Attendance (25.1% vs 32.9%).
   - Optimize WhatsApp/SMS calendar sync and join links specifically for Android users.
