# Cohort Marketing Performance — Full Working Package

A production-grade analytics application and SQL query engine for Cohort Marketing Performance, built with **Python**, **FastAPI**, **SQLAlchemy**, **MariaDB**, **Pydantic**, and **HTML5 / CSS / JavaScript**.

---

## Architecture Overview

```
Cohort-marketing-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (KPIs, Cohorts, Slicers, Devices, Follow-ups)
│   │   ├── core/            # Config, DB connection, resilient fallback
│   │   ├── models/          # Pydantic validation schemas
│   │   ├── services/        # Analytical engine, maturity gating, calculations
│   │   └── main.py          # FastAPI application & static server
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html           # Executive interactive dashboard UI
│   ├── css/styles.css       # Clean design system & styling
│   └── js/                  # App controller, reactive controls, charting, followups
├── queries/
│   ├── 01_production/       # Production SQL (COHORT_MASTER_OPTIMISED, 24_kpi_unified, etc.)
│   └── 02_audits/           # Audit queries (iOS vs Android device comparison, etc.)
├── docs/                    # Formulas, optimization plan, next steps
└── README.md
```

---

## Key Business & Engineering Rules Enforced

1. **The Cohort Rule**:
   - Leads belong permanently to their capture date cohort.
   - For cohort period `Dn`, all events occurring from Day 0 through Day `n` are counted cumulatively.
   - `Till date` runs from capture date through the live database refresh timestamp.
2. **Fixed at D0 vs Moving Metrics**:
   - Fixed at D0: Spend, Impressions, Clicks, Contacts Registered, CPL, CTR. *(Switching D0 → D30 leaves acquisition spend KPI unchanged)*.
   - Moves with Cohort: Demos Booked, Scheduled, Attended, Attendance %, Conversions, Conversion %, New Revenue, ARPU, ROAS.
3. **Maturity Gating**:
   - For `Dn`, a capture date is included only if `capture date + n <= refresh date`. Incomplete windows are dropped completely to avoid artificial dips.
4. **Recalculated Totals**:
   - Volume columns are summed. Every ratio is recalculated from summed numerators and denominators (`Never average ratios`).

---

## Quickstart & Running Locally

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment (Optional MariaDB)
```bash
cp .env.example .env
# Edit .env with your MariaDB credentials if connecting to live database
```

### 3. Start FastAPI Server
```bash
uvicorn backend.app.main:app --reload --port 8000
```

### 4. Open in Browser
- **Dashboard Interface**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Documentation Index

- [`FORMULA_CARD_FOR_DASHBOARD.md`](file:///c:/Users/bisha/OneDrive/Documents/GitHub/Cohort-marketing-dashboard/docs/FORMULA_CARD_FOR_DASHBOARD.md): Metabase-ready formula markdown.
- [`OPTIMISATION_PLAN.md`](file:///c:/Users/bisha/OneDrive/Documents/GitHub/Cohort-marketing-dashboard/docs/OPTIMISATION_PLAN.md): 5-phase DB performance & caching plan.
- [`NEXT_STEPS.md`](file:///c:/Users/bisha/OneDrive/Documents/GitHub/Cohort-marketing-dashboard/docs/NEXT_STEPS.md): Outstanding engineering & CRO items.
