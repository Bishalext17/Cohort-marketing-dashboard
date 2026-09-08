### Cohort Marketing Dashboard — Formula Reference Card

#### 1. The Core Ratios (Plain Words)
- **CPL (Cost Per Lead)** = `Total Spend ÷ Contacts Registered`
- **Demo Attendance %** = `Demos Attended ÷ Contacts Registered` *(Denominator is ALL leads captured, not just scheduled demos)*
- **Conversion %** = `Paying Conversions ÷ Contacts Registered`
- **ARPU (Average Revenue Per User)** = `New Revenue ÷ Conversions`
- **ROAS (Return on Ad Spend)** = `New Revenue ÷ Total Spend`
- **CTR (Click-Through Rate)** = `Clicks ÷ Impressions`

---

#### 2. The Cohort Rule
- A lead belongs permanently to the date it was captured.
- **`Dn`** means **all events occurring from Day 0 through Day `n`** (Cumulative).
- **`Till Date`** means from capture date through the live database refresh timestamp.

---

#### 3. What Moves vs What Stays Fixed
- **Fixed at D0**: Spend, Impressions, Clicks, Contacts Registered, CPL, CTR. *(Switching D0 → D30 MUST NOT change total spend)*.
- **Moves with Cohort Window**: Demos Booked, Scheduled, Attended, Conversions, New Revenue, ARPU, ROAS.

---

#### 4. The Maturity Gate
- For any window **`Dn`**, capture dates are included **only if `Capture Date + n <= Refresh Date`**.
- Incomplete windows are dropped entirely (not shown as partials) to prevent false dips.

---

#### 5. Golden Rules for Analysis
1. Filter `traffic_type` to `Paid%` before evaluating ROI (Organic represents ~10% leads but ~28% revenue).
2. Filter `data_status` to `Complete` so days missing spend logs are excluded.
3. Use a fixed window (**D3** or **D7**) when evaluating creative/campaign ROAS.
