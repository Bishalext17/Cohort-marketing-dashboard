from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import logging
import time
from backend.app.models.schemas import (
    FilterParams, KPITile, KPITilesResponse, CohortTableRow, CohortMasterResponse,
    MaturityDay, CohortMaturityResponse, DeviceComparisonResponse, DeviceMetric,
    FollowUpContact, FollowUpListResponse
)
from backend.app.services.mock_data import get_raw_seed_data
from backend.app.services.sql_engine import sql_engine
from backend.app.services.cache_manager import cache_manager
from backend.app.core.database import check_db_connection

logger = logging.getLogger(__name__)

class CohortAnalyticsService:
    def __init__(self):
        self.raw = get_raw_seed_data()
        self.spend_records = self._generate_spend_data()
        self.lead_records = self._generate_lead_data()
        self.lead_status_overrides: Dict[str, Dict[str, Any]] = {}
        
        # Start async pre-warmer if loop is available
        try:
            cache_manager.start_background_prewarmer(self)
        except Exception:
            pass

    def _get_cache_key(self, prefix: str, filters: FilterParams) -> str:
        slicers = sorted(filters.slicers or [])
        return f"{prefix}:{filters.cohort_period}:{filters.date_from}:{filters.date_to}:{slicers}:{filters.campaign_names}:{filters.countries}"

    def _get_from_cache(self, key: str, force_refresh: bool = False) -> Optional[Any]:
        if force_refresh:
            return None
        return cache_manager.get(key)

    def _set_cache(self, key: str, data: Any):
        cache_manager.set(key, data)

    def _generate_spend_data(self) -> List[Dict[str, Any]]:
        records = []
        combos = self.raw["combos"]
        days = self.raw["meta"]["days"]
        
        for d in range(days):
            for c_idx, combo in enumerate(combos):
                base_spend = 1200 + ((d * 37 + c_idx * 73) % 4500)
                impressions = int(base_spend * (3.5 + ((d + c_idx) % 4)))
                clicks = int(impressions * (0.015 + ((c_idx % 5) * 0.003)))
                leads = int(clicks * (0.65 + ((d % 3) * 0.05)))
                
                records.append({
                    "day": d,
                    "combo_idx": c_idx,
                    "spend": round(base_spend, 2),
                    "impressions": impressions,
                    "clicks": clicks,
                    "contacts_registered": leads,
                    "fb_results": leads
                })
        return records

    def _generate_lead_data(self) -> List[Dict[str, Any]]:
        leads = []
        lead_counter = 100000
        days = self.raw["meta"]["days"]
        combos = self.raw["combos"]

        for d in range(days):
            for c_idx, combo in enumerate(combos):
                country_idx = combo[4]
                num_leads = 2 + ((d * 7 + c_idx * 11) % 18)
                
                for i in range(num_leads):
                    lead_counter += 1
                    lead_id = f"LD{lead_counter}"
                    
                    has_booked = (lead_counter % 10) < 6
                    booked_d = (lead_counter % 3) if has_booked else -1
                    sched_d = (booked_d + (lead_counter % 2)) if has_booked else -1
                    
                    is_ios = (lead_counter % 3) == 0
                    att_chance = 33 if is_ios else 25
                    has_attended = has_booked and ((lead_counter * 13) % 100 < att_chance)
                    att_d = (sched_d + (lead_counter % 3)) if has_attended else -1
                    
                    conv_chance = 35 if (has_attended and is_ios) else (14 if has_attended else 0)
                    has_conv = has_attended and ((lead_counter * 17) % 100 < conv_chance)
                    conv_d = (att_d + (lead_counter % 4)) if has_conv else -1
                    
                    base_price = 45000 if country_idx != 3 else 18500
                    rev = base_price if has_conv else 0.0

                    leads.append({
                        "lead_id": lead_id,
                        "day": d,
                        "combo_idx": c_idx,
                        "booked_d": booked_d,
                        "sched_d": sched_d,
                        "att_d": att_d,
                        "conv_d": conv_d,
                        "revenue": rev,
                        "is_ios": is_ios
                    })
        return leads

    def _parse_cohort_offset(self, cohort_period: str) -> Optional[int]:
        if not cohort_period or cohort_period.lower() == "till date":
            return None
        if cohort_period.upper().startswith("D"):
            try:
                return int(cohort_period[1:])
            except ValueError:
                return None
        return None

    def filter_combos(self, filters: FilterParams) -> List[int]:
        matching_indices = []
        combos = self.raw["combos"]
        
        for idx, combo in enumerate(combos):
            camp = self.raw["campaigns"][combo[0]]
            adset = self.raw["adsets"][combo[1]]
            ad = self.raw["ads"][combo[2]]
            channel = self.raw["channels"][combo[3]]
            country = self.raw["countries"][combo[4]]
            platform = self.raw["platforms"][combo[5]]
            course = self.raw["courses"][combo[6]]

            if filters.channels and channel not in filters.channels:
                continue
            if filters.countries and country not in filters.countries:
                continue
            if filters.platforms and platform not in filters.platforms:
                continue
            if filters.courses and course not in filters.courses:
                continue
            if filters.campaign_ids and camp["id"] not in filters.campaign_ids:
                continue
            if filters.campaign_names and camp["name"] not in filters.campaign_names:
                continue
            if filters.adset_ids and adset["id"] not in filters.adset_ids:
                continue
            if filters.adset_names and adset["name"] not in filters.adset_names:
                continue
            if filters.ad_ids and ad["id"] not in filters.ad_ids:
                continue
            if filters.ad_names and ad["name"] not in filters.ad_names:
                continue
            
            matching_indices.append(idx)
        return matching_indices

    def get_maturity_data(self, cohort_period: str, filters: FilterParams) -> CohortMaturityResponse:
        cache_key = self._get_cache_key("maturity", filters)
        cached = self._get_from_cache(cache_key, force_refresh=bool(filters.force_refresh))
        if cached:
            return cached

        offset = self._parse_cohort_offset(cohort_period)
        start_str = filters.date_from or "2026-07-01"
        end_str = filters.date_to or "2026-07-31"
        
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
            if start_date > end_date:
                start_date, end_date = end_date, start_date
            days = max(1, (end_date - start_date).days + 1)
        except Exception:
            start_date = datetime(2026, 7, 1)
            end_date = datetime(2026, 7, 31)
            days = 31
            
        today = datetime.now()
        days_list = []
        counted_count = 0
        dropped_count = 0

        base_start = datetime.strptime(self.raw["meta"]["start"], "%Y-%m-%d")
        valid_combos = set(self.filter_combos(filters))
        daily_leads: Dict[str, int] = {}
        daily_att: Dict[str, int] = {}
        daily_conv: Dict[str, int] = {}
        daily_rev: Dict[str, float] = {}

        for ld in self.lead_records:
            if ld["combo_idx"] not in valid_combos:
                continue
            d_str = (base_start + timedelta(days=ld["day"])).strftime("%Y-%m-%d")
            daily_leads[d_str] = daily_leads.get(d_str, 0) + 1
            if ld["att_d"] >= 0:
                daily_att[d_str] = daily_att.get(d_str, 0) + 1
            if ld["conv_d"] >= 0:
                daily_conv[d_str] = daily_conv.get(d_str, 0) + 1
                daily_rev[d_str] = daily_rev.get(d_str, 0.0) + ld["revenue"]

        for d in range(days):
            curr_date_dt = start_date + timedelta(days=d)
            curr_date = curr_date_dt.strftime("%Y-%m-%d")
            
            if offset is None:
                is_mature = True
            else:
                is_mature = (curr_date_dt + timedelta(days=offset) <= today)
                
            status = "counted" if is_mature else "dropped"
            
            if is_mature:
                counted_count += 1
            else:
                dropped_count += 1
            
            days_list.append(MaturityDay(
                date=curr_date,
                day_num=d+1,
                status=status,
                is_mature=is_mature,
                leads_captured=daily_leads.get(curr_date, 0),
                attended_count=daily_att.get(curr_date, 0),
                conversions_count=daily_conv.get(curr_date, 0),
                revenue=daily_rev.get(curr_date, 0.0)
            ))

        if offset is None:
            note = "Till date includes all capture dates through refresh timestamp. No maturity gate applied."
        else:
            note = f"For cohort D{offset}, {dropped_count} days are dropped (window not yet closed) to prevent false performance drops."

        res = CohortMaturityResponse(
            selected_cohort=cohort_period,
            refresh_date=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            total_dates=days,
            counted_dates=counted_count,
            dropped_dates=dropped_count,
            note=note,
            days=days_list
        )
        self._set_cache(cache_key, res)
        return res

    def calculate_cohort_performance(self, filters: FilterParams) -> CohortMasterResponse:
        cache_key = self._get_cache_key("master", filters)
        cached = self._get_from_cache(cache_key, force_refresh=bool(filters.force_refresh))
        if cached:
            return cached

        # Check if live database is connected
        if check_db_connection():
            try:
                from_date = filters.date_from or "2026-07-01"
                to_date = filters.date_to or "2026-07-31"
                if from_date > to_date:
                    from_date, to_date = to_date, from_date
                offset = self._parse_cohort_offset(filters.cohort_period)
                cohort_days = 9999 if offset is None else offset
                
                # Execute Production COHORT_MASTER_OPTIMISED Query
                raw_sql = sql_engine.read_query("01_production/COHORT_MASTER_OPTIMISED.sql")
                params = {
                    "from_date": from_date,
                    "to_date": to_date,
                    "cohort_days": cohort_days,
                    "campaign_nm": filters.campaign_names if filters.campaign_names else None,
                    "country_cd": filters.countries[0] if (filters.countries and len(filters.countries) == 1) else None
                }
                res = sql_engine.execute_query(raw_sql, params)
                if res.get("success") and res.get("rows"):
                    # Slicers requested (defaults to ["date"] if empty)
                    slicers = filters.slicers if (filters.slicers and len(filters.slicers) > 0) else ["date"]
                    
                    dim_labels = {
                        "date": "Lead Capture Date",
                        "campaign": "Campaign Name",
                        "adset": "Ad Set Name",
                        "ad": "Ad Name",
                        "country": "Country",
                        "channel": "Channel",
                        "platform": "Platform",
                        "course": "Course"
                    }
                    headers = [{"key": s, "label": dim_labels.get(s, s.replace("_", " ").title())} for s in slicers]
                    headers.extend([
                        {"key": "spend", "label": "Spend (₹)"},
                        {"key": "impressions", "label": "Impressions"},
                        {"key": "clicks", "label": "Clicks"},
                        {"key": "contacts_registered", "label": "Contacts Reg."},
                        {"key": "cpl", "label": "CPL (₹)"},
                        {"key": "demos_booked", "label": "Demos Booked"},
                        {"key": "demos_attended", "label": "Demos Attended"},
                        {"key": "attendance_pct", "label": "Attendance %"},
                        {"key": "conversions", "label": "Conversions"},
                        {"key": "conversion_pct", "label": "Conversion %"},
                        {"key": "new_revenue", "label": "New Rev (₹)"},
                        {"key": "arpu", "label": "ARPU (₹)"},
                        {"key": "roas", "label": "ROAS"}
                    ])

                    groups: Dict[str, Dict[str, Any]] = {}
                    tot_spend = 0.0
                    tot_imp = 0
                    tot_clk = 0
                    tot_ct = 0
                    tot_bk = 0
                    tot_sc = 0
                    tot_at = 0
                    tot_cv = 0
                    tot_rv = 0.0

                    for r in res["rows"]:
                        row_type = str(r.get("row_type") or "").strip().upper()
                        if row_type == "TOTAL":
                            continue

                        capture_date = str(r.get("lead_capture_date") or r.get("d1") or r.get("lead_capture_period") or "")
                        campaign = str(r.get("campaign_name") or r.get("campaign") or "")
                        adset = str(r.get("adset_name") or r.get("adsets_merged") or r.get("adset") or "")
                        ad = str(r.get("ad_name") or r.get("ad") or "")
                        country = str(r.get("country_code") or r.get("country") or "")

                        if filters.campaign_names and campaign not in filters.campaign_names:
                            continue
                        if filters.adset_names and adset not in filters.adset_names:
                            continue
                        if filters.ad_names and ad not in filters.ad_names:
                            continue
                        if filters.countries and country not in filters.countries:
                            continue

                        sp = float(r.get("spend") or 0.0)
                        imp = int(r.get("impressions") or 0)
                        clk = int(r.get("clicks") or 0)
                        ct = int(r.get("contacts_registered") or 0)
                        bk = int(r.get("demos_booked") or 0)
                        sc = int(r.get("demos_scheduled") or 0)
                        at = int(r.get("demos_attended") or 0)
                        cv = int(r.get("conversions") or r.get("conversions_first_time") or 0)
                        rv = float(r.get("new_revenue") or r.get("new_revenue_first_time") or 0.0)

                        dim_vals = {}
                        for s in slicers:
                            if s == "date":
                                dim_vals["date"] = capture_date
                            elif s == "campaign":
                                dim_vals["campaign"] = campaign
                            elif s == "adset":
                                dim_vals["adset"] = adset
                            elif s == "ad":
                                dim_vals["ad"] = ad
                            elif s == "country":
                                dim_vals["country"] = country
                            else:
                                dim_vals[s] = str(r.get(s) or "")

                        group_key = json.dumps(dim_vals, sort_keys=True)
                        if group_key not in groups:
                            groups[group_key] = {
                                "dimensions": dim_vals,
                                "spend": 0.0,
                                "impressions": 0,
                                "clicks": 0,
                                "contacts_registered": 0,
                                "demos_booked": 0,
                                "demos_scheduled": 0,
                                "demos_attended": 0,
                                "conversions": 0,
                                "new_revenue": 0.0
                            }

                        g = groups[group_key]
                        g["spend"] += sp
                        g["impressions"] += imp
                        g["clicks"] += clk
                        g["contacts_registered"] += ct
                        g["demos_booked"] += bk
                        g["demos_scheduled"] += sc
                        g["demos_attended"] += at
                        g["conversions"] += cv
                        g["new_revenue"] += rv

                        tot_spend += sp
                        tot_imp += imp
                        tot_clk += clk
                        tot_ct += ct
                        tot_bk += bk
                        tot_sc += sc
                        tot_at += at
                        tot_cv += cv
                        tot_rv += rv

                    rows = []
                    for key, g in groups.items():
                        sp = round(g["spend"], 2)
                        imp = g["impressions"]
                        clk = g["clicks"]
                        ct = g["contacts_registered"]
                        bk = g["demos_booked"]
                        sc = g["demos_scheduled"]
                        at = g["demos_attended"]
                        cv = g["conversions"]
                        rv = round(g["new_revenue"], 2)

                        cpl = round((sp / ct), 2) if ct > 0 else 0.0
                        ctr = round((clk / imp * 100), 2) if imp > 0 else 0.0
                        att_pct = round((at / ct * 100), 2) if ct > 0 else 0.0
                        conv_pct = round((cv / ct * 100), 2) if ct > 0 else 0.0
                        arpu = round((rv / cv), 2) if cv > 0 else 0.0
                        roas = round((rv / sp), 2) if sp > 0 else 0.0

                        rows.append(CohortTableRow(
                            dimensions=g["dimensions"],
                            spend=sp,
                            impressions=imp,
                            clicks=clk,
                            contacts_registered=ct,
                            ctr_pct=ctr,
                            cpl=cpl,
                            demos_booked=bk,
                            demos_scheduled=sc,
                            demos_attended=at,
                            attendance_pct=att_pct,
                            conversions=cv,
                            conversion_pct=conv_pct,
                            new_revenue=rv,
                            arpu=arpu,
                            roas=roas
                        ))

                    totals = CohortTableRow(
                        dimensions={slicers[0]: "TOTAL", "label": "TOTAL"},
                        spend=round(tot_spend, 2),
                        impressions=tot_imp,
                        clicks=tot_clk,
                        contacts_registered=tot_ct,
                        ctr_pct=round((tot_clk / tot_imp * 100), 2) if tot_imp > 0 else 0.0,
                        cpl=round((tot_spend / tot_ct), 2) if tot_ct > 0 else 0.0,
                        demos_booked=tot_bk,
                        demos_scheduled=tot_sc,
                        demos_attended=tot_at,
                        attendance_pct=round((tot_at / tot_ct * 100), 2) if tot_ct > 0 else 0.0,
                        conversions=tot_cv,
                        conversion_pct=round((tot_cv / tot_ct * 100), 2) if tot_ct > 0 else 0.0,
                        new_revenue=round(tot_rv, 2),
                        arpu=round((tot_rv / tot_cv), 2) if tot_cv > 0 else 0.0,
                        roas=round((tot_rv / tot_spend), 2) if tot_spend > 0 else 0.0
                    )

                    response = CohortMasterResponse(
                        headers=headers,
                        rows=rows,
                        totals=totals,
                        row_count=len(rows),
                        applied_cohort=filters.cohort_period,
                        applied_filters=filters.model_dump()
                    )
                    self._set_cache(cache_key, response)
                    return response
            except Exception as e:
                logger.error(f"Error executing live sliced query, falling back to simulator: {e}")

        # Fallback to simulation
        offset = self._parse_cohort_offset(filters.cohort_period)
        days = self.raw["meta"]["days"]
        start_date = datetime.strptime(self.raw["meta"]["start"], "%Y-%m-%d")
        valid_combos = set(self.filter_combos(filters))
        
        try:
            filter_from_dt = datetime.strptime(filters.date_from, "%Y-%m-%d") if filters.date_from else start_date
        except Exception:
            filter_from_dt = start_date
            
        try:
            filter_to_dt = datetime.strptime(filters.date_to, "%Y-%m-%d") if filters.date_to else (start_date + timedelta(days=days - 1))
        except Exception:
            filter_to_dt = start_date + timedelta(days=days - 1)

        if filter_from_dt > filter_to_dt:
            filter_from_dt, filter_to_dt = filter_to_dt, filter_from_dt

        mature_days = set()
        for d in range(days):
            curr_date = start_date + timedelta(days=d)
            if filter_from_dt <= curr_date <= filter_to_dt:
                if offset is None or (d + offset < days):
                    mature_days.add(d)

        slicers = filters.slicers if (filters.slicers and len(filters.slicers) > 0) else ["date"]
        groups: Dict[str, Dict[str, Any]] = {}

        for sp in self.spend_records:
            if sp["day"] not in mature_days or sp["combo_idx"] not in valid_combos:
                continue
            c_idx = sp["combo_idx"]
            combo = self.raw["combos"][c_idx]
            dim_values = self._extract_dimension_values(sp["day"], combo, slicers, start_date)
            group_key = json.dumps(dim_values, sort_keys=True)
            if group_key not in groups:
                groups[group_key] = self._init_group_data(dim_values)
            g = groups[group_key]
            g["spend"] += sp["spend"]
            g["impressions"] += sp["impressions"]
            g["clicks"] += sp["clicks"]
            g["contacts_registered"] += sp["contacts_registered"]

        max_d = 999999 if offset is None else offset
        for ld in self.lead_records:
            if ld["day"] not in mature_days or ld["combo_idx"] not in valid_combos:
                continue
            c_idx = ld["combo_idx"]
            combo = self.raw["combos"][c_idx]
            dim_values = self._extract_dimension_values(ld["day"], combo, slicers, start_date)
            group_key = json.dumps(dim_values, sort_keys=True)
            if group_key not in groups:
                groups[group_key] = self._init_group_data(dim_values)
            g = groups[group_key]
            if 0 <= ld["booked_d"] <= max_d:
                g["demos_booked"] += 1
            if 0 <= ld["sched_d"] <= max_d:
                g["demos_scheduled"] += 1
            if 0 <= ld["att_d"] <= max_d:
                g["demos_attended"] += 1
            if 0 <= ld["conv_d"] <= max_d:
                g["conversions"] += 1
                g["new_revenue"] += ld["revenue"]

        rows: List[CohortTableRow] = []
        tot_spend = 0.0
        tot_imp = 0
        tot_clicks = 0
        tot_contacts = 0
        tot_booked = 0
        tot_sched = 0
        tot_att = 0
        tot_conv = 0
        tot_rev = 0.0

        for key, g in groups.items():
            spend = round(g["spend"], 2)
            imp = g["impressions"]
            clk = g["clicks"]
            contacts = g["contacts_registered"]
            booked = g["demos_booked"]
            sched = g["demos_scheduled"]
            att = g["demos_attended"]
            conv = g["conversions"]
            rev = round(g["new_revenue"], 2)

            ctr = round((clk / imp * 100), 2) if imp > 0 else 0.0
            cpl = round((spend / contacts), 2) if contacts > 0 else 0.0
            att_pct = round((att / contacts * 100), 2) if contacts > 0 else 0.0
            conv_pct = round((conv / contacts * 100), 2) if contacts > 0 else 0.0
            arpu = round((rev / conv), 2) if conv > 0 else 0.0
            roas = round((rev / spend), 2) if spend > 0 else 0.0

            rows.append(CohortTableRow(
                dimensions=g["dimensions"],
                spend=spend,
                impressions=imp,
                clicks=clk,
                contacts_registered=contacts,
                ctr_pct=ctr,
                cpl=cpl,
                demos_booked=booked,
                demos_scheduled=sched,
                demos_attended=att,
                attendance_pct=att_pct,
                conversions=conv,
                conversion_pct=conv_pct,
                new_revenue=rev,
                arpu=arpu,
                roas=roas
            ))

            tot_spend += spend
            tot_imp += imp
            tot_clicks += clk
            tot_contacts += contacts
            tot_booked += booked
            tot_sched += sched
            tot_att += att
            tot_conv += conv
            tot_rev += rev

        tot_ctr = round((tot_clicks / tot_imp * 100), 2) if tot_imp > 0 else 0.0
        tot_cpl = round((tot_spend / tot_contacts), 2) if tot_contacts > 0 else 0.0
        tot_att_pct = round((tot_att / tot_contacts * 100), 2) if tot_contacts > 0 else 0.0
        tot_conv_pct = round((tot_conv / tot_contacts * 100), 2) if tot_contacts > 0 else 0.0
        tot_arpu = round((tot_rev / tot_conv), 2) if tot_conv > 0 else 0.0
        tot_roas = round((tot_rev / tot_spend), 2) if tot_spend > 0 else 0.0

        totals = CohortTableRow(
            dimensions={slicers[0]: "TOTAL", "label": "TOTAL"},
            spend=round(tot_spend, 2),
            impressions=tot_imp,
            clicks=tot_clicks,
            contacts_registered=tot_contacts,
            ctr_pct=tot_ctr,
            cpl=tot_cpl,
            demos_booked=tot_booked,
            demos_scheduled=tot_sched,
            demos_attended=tot_att,
            attendance_pct=tot_att_pct,
            conversions=tot_conv,
            conversion_pct=tot_conv_pct,
            new_revenue=round(tot_rev, 2),
            arpu=tot_arpu,
            roas=tot_roas
        )

        dim_labels = {
            "date": "Lead Capture Date",
            "campaign": "Campaign Name",
            "adset": "Ad Set Name",
            "ad": "Ad Name",
            "country": "Country",
            "channel": "Channel",
            "platform": "Platform",
            "course": "Course"
        }
        headers = []
        for s in slicers:
            headers.append({"key": s, "label": dim_labels.get(s, s.replace("_", " ").title())})
        headers.extend([
            {"key": "spend", "label": "Spend (₹)"},
            {"key": "impressions", "label": "Impressions"},
            {"key": "clicks", "label": "Clicks"},
            {"key": "contacts_registered", "label": "Contacts Reg."},
            {"key": "cpl", "label": "CPL (₹)"},
            {"key": "demos_booked", "label": "Demos Booked"},
            {"key": "demos_attended", "label": "Demos Attended"},
            {"key": "attendance_pct", "label": "Attendance %"},
            {"key": "conversions", "label": "Conversions"},
            {"key": "conversion_pct", "label": "Conversion %"},
            {"key": "new_revenue", "label": "New Rev (₹)"},
            {"key": "arpu", "label": "ARPU (₹)"},
            {"key": "roas", "label": "ROAS"}
        ])

        response = CohortMasterResponse(
            headers=headers,
            rows=rows,
            totals=totals,
            row_count=len(rows),
            applied_cohort=filters.cohort_period,
            applied_filters=filters.model_dump()
        )
        self._set_cache(cache_key, response)
        return response

    def get_kpis(self, filters: FilterParams) -> KPITilesResponse:
        # Check master table cache first
        master_key = self._get_cache_key("master", filters)
        cached_master = self._get_from_cache(master_key)
        if cached_master:
            tot = cached_master.totals
            return self._build_kpi_response(tot, filters.cohort_period)

        # Check if live database is connected
        if check_db_connection():
            try:
                # Use calculate_cohort_performance to compute and cache everything at once!
                master = self.calculate_cohort_performance(filters)
                return self._build_kpi_response(master.totals, filters.cohort_period)
            except Exception as e:
                logger.error(f"Error executing live KPI query, falling back: {e}")

        # Fallback to simulation
        master = self.calculate_cohort_performance(filters)
        return self._build_kpi_response(master.totals, filters.cohort_period)

    def _build_kpi_response(self, tot: CohortTableRow, cohort_period: str) -> KPITilesResponse:
        return KPITilesResponse(
            spend=KPITile(
                key="spend",
                label="Spend",
                value=f"₹{tot.spend:,.2f}",
                numeric_value=tot.spend,
                description="Acquisition spend across mature days (fixed D0)",
                format_type="currency"
            ),
            leads=KPITile(
                key="leads",
                label="Contacts Registered",
                value=f"{tot.contacts_registered:,}",
                numeric_value=float(tot.contacts_registered),
                description="Total unique registered leads",
                format_type="number"
            ),
            cpl=KPITile(
                key="cpl",
                label="Cost Per Lead (CPL)",
                value=f"₹{tot.cpl:,.2f}",
                numeric_value=tot.cpl,
                description="Spend ÷ Contacts Registered",
                format_type="currency"
            ),
            demos_attended=KPITile(
                key="demos_attended",
                label="Demos Attended",
                value=f"{tot.demos_attended:,}",
                numeric_value=float(tot.demos_attended),
                description=f"Attended demos in {cohort_period}",
                format_type="number"
            ),
            attendance_pct=KPITile(
                key="attendance_pct",
                label="Attendance Rate",
                value=f"{tot.attendance_pct:.1f}%",
                numeric_value=tot.attendance_pct,
                description="Demos Attended ÷ Contacts Registered",
                format_type="percentage"
            ),
            conversions=KPITile(
                key="conversions",
                label="Conversions",
                value=f"{tot.conversions:,}",
                numeric_value=float(tot.conversions),
                description=f"Paying customers in {cohort_period}",
                format_type="number"
            ),
            conversion_pct=KPITile(
                key="conversion_pct",
                label="Conversion Rate",
                value=f"{tot.conversion_pct:.2f}%",
                numeric_value=tot.conversion_pct,
                description="Conversions ÷ Contacts Registered",
                format_type="percentage"
            ),
            revenue=KPITile(
                key="revenue",
                label="New Revenue",
                value=f"₹{tot.new_revenue:,.2f}",
                numeric_value=tot.new_revenue,
                description=f"Revenue realized in {cohort_period}",
                format_type="currency"
            ),
            arpu=KPITile(
                key="arpu",
                label="ARPU (Paying)",
                value=f"₹{tot.arpu:,.2f}",
                numeric_value=tot.arpu,
                description="Revenue ÷ Conversions",
                format_type="currency"
            ),
            roas=KPITile(
                key="roas",
                label="New Rev ROAS",
                value=f"{tot.roas:.2f}x",
                numeric_value=tot.roas,
                description="New Revenue ÷ Spend",
                format_type="number"
            ),
            impressions=KPITile(
                key="impressions",
                label="Impressions",
                value=f"{int(tot.impressions):,}",
                numeric_value=float(tot.impressions),
                description="Total ad impressions",
                format_type="number"
            ),
            clicks=KPITile(
                key="clicks",
                label="Clicks",
                value=f"{int(tot.clicks):,}",
                numeric_value=float(tot.clicks),
                description="Total ad clicks",
                format_type="number"
            ),
            ctr=KPITile(
                key="ctr",
                label="Click-Through Rate (CTR)",
                value=f"{tot.ctr_pct:.2f}%",
                numeric_value=tot.ctr_pct,
                description="Clicks ÷ Impressions",
                format_type="percentage"
            )
        )

    def get_device_comparison(self) -> DeviceComparisonResponse:
        ios_leads = [ld for ld in self.lead_records if ld["is_ios"]]
        android_leads = [ld for ld in self.lead_records if not ld["is_ios"]]
        
        tot_leads = len(self.lead_records)
        ios_cnt = len(ios_leads)
        android_cnt = len(android_leads)

        ios_booked = sum(1 for ld in ios_leads if ld["booked_d"] >= 0)
        android_booked = sum(1 for ld in android_leads if ld["booked_d"] >= 0)

        ios_att = sum(1 for ld in ios_leads if ld["att_d"] >= 0)
        android_att = sum(1 for ld in android_leads if ld["att_d"] >= 0)

        ios_conv = sum(1 for ld in ios_leads if ld["conv_d"] >= 0)
        android_conv = sum(1 for ld in android_leads if ld["conv_d"] >= 0)

        ios_rev = sum(ld["revenue"] for ld in ios_leads)
        android_rev = sum(ld["revenue"] for ld in android_leads)

        ios_conv_rate = (ios_conv / ios_cnt * 100) if ios_cnt > 0 else 0.0
        android_conv_rate = (android_conv / android_cnt * 100) if android_cnt > 0 else 0.0
        ratio = round(ios_conv_rate / android_conv_rate, 2) if android_conv_rate > 0 else 1.0

        devices = [
            DeviceMetric(
                os="iOS",
                leads=ios_cnt,
                leads_share_pct=round(ios_cnt / tot_leads * 100, 1),
                booked=ios_booked,
                booked_pct=round(ios_booked / ios_cnt * 100, 1),
                attended=ios_att,
                attended_pct=round(ios_att / ios_cnt * 100, 1),
                conversions=ios_conv,
                conversion_pct=round(ios_conv_rate, 2),
                revenue=ios_rev,
                arpu=round(ios_rev / ios_conv, 2) if ios_conv > 0 else 0.0,
                conversion_ratio_vs_android=ratio
            ),
            DeviceMetric(
                os="Android",
                leads=android_cnt,
                leads_share_pct=round(android_cnt / tot_leads * 100, 1),
                booked=android_booked,
                booked_pct=round(android_booked / android_cnt * 100, 1),
                attended=android_att,
                attended_pct=round(android_att / android_cnt * 100, 1),
                conversions=android_conv,
                conversion_pct=round(android_conv_rate, 2),
                revenue=android_rev,
                arpu=round(android_rev / android_conv, 2) if android_conv > 0 else 0.0,
                conversion_ratio_vs_android=1.0
            )
        ]

        return DeviceComparisonResponse(
            title="Gita Platform & Device Funnel Audit (August/September 2026)",
            summary_insight=f"iOS converts {ratio}× higher than Android. Booking rates are virtually identical (~60%), but Android drops at Attendance ({devices[1].attended_pct}% vs {devices[0].attended_pct}%). This points to SMS/WhatsApp reminder and join flow friction on Android rather than audience quality.",
            devices=devices
        )

    def get_followup_contacts(self, category: str = "all") -> FollowUpListResponse:
        contacts: List[FollowUpContact] = []
        combos = self.raw["combos"]
        courses = self.raw["courses"]
        campaigns = self.raw["campaigns"]

        for i, ld in enumerate(self.lead_records[:2000]):
            combo = combos[ld["combo_idx"]]
            course_name = courses[combo[6]]
            camp_name = campaigns[combo[0]]["name"]
            os_name = "iOS" if ld["is_ios"] else "Android"
            
            attended = ld["att_d"] >= 0
            converted = ld["conv_d"] >= 0
            
            if category == "conversions_14d" and not converted:
                continue
            elif category == "attended_not_paid" and (not attended or converted):
                continue
            elif category == "demos_booked_3d" and (ld["booked_d"] < 0 or attended or converted):
                continue

            status_label = "Converted" if converted else ("Attended (Unpaid)" if attended else ("Booked (Not Attended)" if ld["booked_d"] >= 0 else "Registered"))
            priority = "High" if attended and not converted else ("Medium" if ld["booked_d"] >= 0 else "Low")

            phone_suffix = 1000 + (i % 9000)
            phone = f"+91 98765 {phone_suffix}"
            parent_name = f"Parent_{ld['lead_id']}"

            override = self.lead_status_overrides.get(ld["lead_id"], {})
            if override.get("status"):
                status_label = override["status"]
            if override.get("followup_priority"):
                priority = override["followup_priority"]
            notes = override.get("notes")

            contacts.append(FollowUpContact(
                lead_id=ld["lead_id"],
                phone=phone,
                parent_name=parent_name,
                lead_date=(datetime.strptime(self.raw["meta"]["start"], "%Y-%m-%d") + timedelta(days=ld["day"])).strftime("%Y-%m-%d"),
                course=course_name,
                campaign_name=camp_name,
                os_family=os_name,
                status=status_label,
                attended=attended,
                converted=converted,
                amount=ld["revenue"],
                days_since_lead=ld["day"],
                followup_priority=priority,
                notes=notes
            ))

        tot_amount = sum(c.amount for c in contacts)
        return FollowUpListResponse(
            category=category,
            count=len(contacts),
            total_potential_or_actual_revenue=tot_amount,
            contacts=contacts
        )

    def update_lead_status(self, lead_id: str, status: Optional[str] = None, priority: Optional[str] = None, notes: Optional[str] = None) -> Optional[FollowUpContact]:
        if lead_id not in self.lead_status_overrides:
            self.lead_status_overrides[lead_id] = {}
        if status is not None:
            self.lead_status_overrides[lead_id]["status"] = status
        if priority is not None:
            self.lead_status_overrides[lead_id]["followup_priority"] = priority
        if notes is not None:
            self.lead_status_overrides[lead_id]["notes"] = notes
        
        all_contacts = self.get_followup_contacts("all").contacts
        for c in all_contacts:
            if c.lead_id == lead_id:
                return c
        return None

    def _extract_dimension_values(self, day: int, combo: List[int], slicers: List[str], start_date: datetime) -> Dict[str, Any]:
        if not slicers:
            return {"All": "Total Portfolio"}
        
        values = {}
        for s in slicers:
            if s in ("date", "lead_date", "lead_capture_date"):
                values["date"] = (start_date + timedelta(days=day)).strftime("%Y-%m-%d")
            elif s == "channel":
                values["channel"] = self.raw["channels"][combo[3]]
            elif s == "platform":
                values["platform"] = self.raw["platforms"][combo[5]]
            elif s == "country":
                values["country"] = self.raw["countries"][combo[4]]
            elif s == "course":
                values["course"] = self.raw["courses"][combo[6]]
            elif s == "campaign":
                camp = self.raw["campaigns"][combo[0]]
                values["campaign"] = camp["name"]
                values["campaign_id"] = camp["id"]
                values["campaign_name"] = camp["name"]
            elif s == "adset":
                adset = self.raw["adsets"][combo[1]]
                values["adset"] = adset["name"]
                values["adset_id"] = adset["id"]
                values["adset_name"] = adset["name"]
            elif s == "ad":
                ad = self.raw["ads"][combo[2]]
                values["ad"] = ad["name"]
                values["ad_id"] = ad["id"]
                values["ad_name"] = ad["name"]
        return values

    def _init_group_data(self, dim_values: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "dimensions": dim_values,
            "spend": 0.0,
            "impressions": 0,
            "clicks": 0,
            "contacts_registered": 0,
            "demos_booked": 0,
            "demos_scheduled": 0,
            "demos_attended": 0,
            "conversions": 0,
            "new_revenue": 0.0
        }

cohort_service = CohortAnalyticsService()
