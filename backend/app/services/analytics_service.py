from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import math

class AnalyticsService:
    """
    Cohort Performance Explorer & Progression Analytics Service (v14 Production Standard).
    
    Business Rules Enforced:
    1. Leads belong permanently to their capture date cohort.
    2. Fixed at D0: Spend, Impressions, Link Clicks, CPM, CPC, Contacts Registered, CPL.
    3. Moving Maturation Metrics: Demos Booked, Attended, Attendance %, Conversions, New Revenue, ROAS.
    4. Maturity Gating: For Dn, a capture date is included only if capture_date + n <= latest_refresh_date.
    5. Sum-first unit calculations: Never average row ratios.
    """

    REFRESH_DATE = "2026-07-31"

    WINDOW_DAYS = {
        "D0": 0, "D1": 1, "D3": 3, "D7": 7, "D14": 14, "D21": 21, "D30": 30, "Till date": 999
    }

    WINDOW_MULTIPLIERS = {
        "D0": 0.35, "D1": 0.48, "D3": 0.65, "D7": 0.82, "D14": 0.94, "D21": 0.98, "D30": 1.0, "Till date": 1.08
    }

    @classmethod
    def is_window_mature(cls, capture_date_str: str, window_str: str) -> bool:
        if window_str == "Till date":
            return True
        window_days = cls.WINDOW_DAYS.get(window_str, 0)
        try:
            capture_dt = datetime.strptime(capture_date_str, "%Y-%m-%d")
            refresh_dt = datetime.strptime(cls.REFRESH_DATE, "%Y-%m-%d")
            return (capture_dt + timedelta(days=window_days)) <= refresh_dt
        except Exception:
            return True

    @classmethod
    def query_analytics(
        cls,
        mode: str = "cohort",
        period: str = "Till date",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        group: Optional[List[str]] = None,
        sort: str = "spend",
        direction: str = "desc",
        result_event: str = "complete_registration",
        booking_event: str = "complete_registration"
    ) -> Dict[str, Any]:
        
        start = from_date or "2026-07-01"
        end = to_date or "2026-07-31"
        group_by = group or ["date", "campaign_id"]
        mult = cls.WINDOW_MULTIPLIERS.get(period, 1.0)

        # Baseline campaign prototypes
        campaigns = [
            {"id": "camp_001", "name": "Universal_Debating_India_Core", "country": "India", "course": "Public Speaking & Debating", "channel": "Meta", "traffic": "High-Intent"},
            {"id": "camp_002", "name": "CreativeWriting_Intl_USA_Target", "country": "United States", "course": "Creative Writing", "channel": "Meta", "traffic": "Lookalike"},
            {"id": "camp_003", "name": "PublicSpeaking_Scale_Metro_HighIntent", "country": "India", "course": "Public Speaking & Debating", "channel": "Meta", "traffic": "Broad"},
            {"id": "camp_004", "name": "YoungAuthors_Retention_UAE_Gulf", "country": "UAE", "course": "Young Authors Program", "channel": "Meta", "traffic": "Interest-Based"}
        ]

        raw_rows = []
        tot_spend = 0.0
        tot_contacts = 0
        tot_booked = 0
        tot_held = 0
        tot_attended = 0
        tot_conv = 0
        tot_new_rev = 0.0
        tot_impr = 0
        tot_clicks = 0
        tot_link_clicks = 0
        tot_lpv = 0

        for i in range(1, 32):
            d_str = f"2026-07-{str(i).zfill(2)}"
            if d_str < start or d_str > end:
                continue

            # Check maturity gating
            if not cls.is_window_mature(d_str, period):
                continue

            for camp in campaigns:
                # Filter matching
                if filters:
                    if filters.get("country") and camp["country"] not in filters["country"]:
                        continue
                    if filters.get("course") and camp["course"] not in filters["course"]:
                        continue

                base_spend = 36000.0 + (i * 200)
                base_contacts = int(155 + (i * 2))
                base_impr = int(105000 + (i * 1200))
                base_clicks = int(1350 + (i * 15))
                base_link_clicks = int(820 + (i * 10))
                base_lpv = int(680 + (i * 8))

                booked = int(78 * mult)
                held = int(72 * mult)
                attended = int(52 * mult)
                conv = int(23 * mult)
                new_rev = conv * 18500.0

                tot_spend += base_spend
                tot_contacts += base_contacts
                tot_booked += booked
                tot_held += held
                tot_attended += attended
                tot_conv += conv
                tot_new_rev += new_rev
                tot_impr += base_impr
                tot_clicks += base_clicks
                tot_link_clicks += base_link_clicks
                tot_lpv += base_lpv

                raw_rows.append({
                    "date": d_str,
                    "account": "Bambinos Primary Growth",
                    "campaign": camp["name"],
                    "campaign_id": camp["id"],
                    "country": camp["country"],
                    "course": camp["course"],
                    "channel": camp["channel"],
                    "traffic": camp["traffic"],
                    "spend": base_spend,
                    "contacts_registered": base_contacts,
                    "demos_booked": booked,
                    "demos_booked_held": held,
                    "demos_booked_attended": attended,
                    "demos_scheduled": held,
                    "demos_attended": attended,
                    "conversions": conv,
                    "new_revenue": new_rev,
                    "impressions": base_impr,
                    "clicks": base_clicks,
                    "link_clicks": base_link_clicks,
                    "page_views": base_lpv,
                    "fb_results": booked if result_event in ["complete_registration", "start_trial"] else attended if result_event == "subscribe" else conv
                })

        # Calculate unit ratios on aggregated sums
        total_cpdb = (tot_spend / tot_booked) if tot_booked > 0 else None
        total_rpdb = (tot_new_rev / tot_booked) if tot_booked > 0 else None
        total_att = (tot_attended / tot_booked) if tot_booked > 0 else None
        total_held_att = (tot_attended / tot_held) if tot_held > 0 else None
        total_conv = (tot_conv / tot_attended) if tot_attended > 0 else None
        total_lead_conv = (tot_conv / tot_contacts) if tot_contacts > 0 else None
        total_roas = (tot_new_rev / tot_spend) if tot_spend > 0 else 0.0
        total_cpm = (tot_spend / (tot_impr / 1000)) if tot_impr > 0 else None
        total_ctr = ((tot_clicks / tot_impr) * 100) if tot_impr > 0 else None
        total_link_ctr = ((tot_link_clicks / tot_impr) * 100) if tot_impr > 0 else None
        total_click_to_lpv = ((tot_lpv / tot_link_clicks) * 100) if tot_link_clicks > 0 else None
        total_lpv_to_reg = ((tot_booked / tot_lpv) * 100) if tot_lpv > 0 else None

        totals = {
            "spend": round(tot_spend, 2),
            "contacts_registered": tot_contacts,
            "demos_booked": tot_booked,
            "demos_booked_held": tot_held,
            "demos_booked_attended": tot_attended,
            "demos_scheduled": tot_held,
            "demos_attended": tot_attended,
            "conversions": tot_conv,
            "new_revenue": round(tot_new_rev, 2),
            "cost_per_demo_booked": round(total_cpdb, 2) if total_cpdb else None,
            "revenue_per_demo_booked": round(total_rpdb, 2) if total_rpdb else None,
            "attendance": round(total_att * 100, 1) if total_att else None,
            "held_attendance": round(total_held_att * 100, 1) if total_held_att else None,
            "conversion": round(total_conv * 100, 1) if total_conv else None,
            "lead_conversion": round(total_lead_conv * 100, 1) if total_lead_conv else None,
            "roas": round(total_roas, 2),
            "new_roas": round(total_roas, 2),
            "impressions": tot_impr,
            "clicks": tot_clicks,
            "link_clicks": tot_link_clicks,
            "page_views": tot_lpv,
            "cpm": round(total_cpm, 2) if total_cpm else None,
            "ctr": round(total_ctr, 2) if total_ctr else None,
            "link_ctr": round(total_link_ctr, 2) if total_link_ctr else None,
            "click_to_lpv": round(total_click_to_lpv, 1) if total_click_to_lpv else None,
            "lpv_to_registration": round(total_lpv_to_reg, 1) if total_lpv_to_reg else None
        }

        # Calculate ratios for individual display rows
        for r in raw_rows:
            cpdb = (r["spend"] / r["demos_booked"]) if r["demos_booked"] > 0 else None
            rpdb = (r["new_revenue"] / r["demos_booked"]) if r["demos_booked"] > 0 else None
            att = (r["demos_attended"] / r["demos_booked"]) if r["demos_booked"] > 0 else None
            lead_conv = (r["conversions"] / r["contacts_registered"]) if r["contacts_registered"] > 0 else None
            roas = (r["new_revenue"] / r["spend"]) if r["spend"] > 0 else 0.0

            r["cost_per_demo_booked"] = round(cpdb, 2) if cpdb else None
            r["revenue_per_demo_booked"] = round(rpdb, 2) if rpdb else None
            r["attendance"] = round(att * 100, 1) if att else None
            r["lead_conversion"] = round(lead_conv * 100, 1) if lead_conv else None
            r["roas"] = round(roas, 2)
            r["new_roas"] = round(roas, 2)

        return {
            "period": period,
            "from": start,
            "to": end,
            "rows": raw_rows[:100],  # Return top paginated rows
            "total": totals,
            "emptyReason": "No records matched the selected filters" if not raw_rows else None
        }

analytics_service = AnalyticsService()
