# KPI Tiles — 8-Tile Setup

Two source queries. Five tiles follow the dashboard's cohort filter; three are pinned to a fixed D3 window.

| # | Tile title | Query | First column | Format |
|---|---|---|---|---|
| 1 | Paid Spend | 10A | `spend` | ₹, compact (₹1.5M) |
| 2 | Paid Leads | 10A | `contacts` | number, comma separator |
| 3 | Paid CPL | 10A | `cpl` | ₹, 0 decimals |
| 4 | Demos Booked | 10A | `demos_booked` | number |
| 5 | Show-up % | 10A | `show_up_rate_pct` | 1 decimal, suffix % |
| 6 | Conversion % · D3 | 10B | `conversion_pct` | 2 decimals, suffix % |
| 7 | Paid ROAS · D3 | 10B | `roas` | 2 decimals, suffix x |
| 8 | ARPU · D3 | 10B | `arpu` | ₹, 0 decimals |

---

## Critical Wiring Rule

> [!IMPORTANT]
> **Do not connect the dashboard cohort filter to tiles 6, 7 and 8.**
> Their window is hard-coded to 3 days. If the filter is wired, they inherit "Till date" and ROAS will sag every day as fresh spend lands against leads too young to convert.
> In Metabase: edit dashboard → click the cohort filter → leave those three cards **unmapped**.
> Tiles 1–5 wire to the cohort filter normally.

---

## Why the Two Groups Cover Different Dates

The D3 maturity gate only admits capture dates where `capture_date + 3 <= today`.
With `from_date = 7 Aug` and today being 12 Aug, that's **7–9 Aug only** — three days, against tiles 1–5's six days.

### User Hover Card Descriptions:
- **Tiles 1–5**: *"Paid acquisition volume and cost across all capture dates in the selected window."*
- **Tiles 6–8**: *"Fixed 3-day conversion window so every lead has had equal time to convert."*

---

## When to Move from D3 to D7

D3 is chosen because it's the longest window with enough capture dates *today*. As history builds, D7 captures more of the conversion curve and becomes the better choice.
Switch once D7 has a full week of qualifying capture dates (~19 Aug). Change every literal `3` in `10B_kpi_revenue_d3.sql` to `7` and update tile titles to `· D7`.
