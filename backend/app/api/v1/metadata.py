from fastapi import APIRouter
from datetime import datetime
from backend.app.services.mock_data import get_raw_seed_data
from backend.app.core.database import check_db_connection
from backend.app.services.sql_engine import sql_engine
from typing import Dict, Any

router = APIRouter(prefix="/metadata", tags=["Metadata"])

@router.get("")
def get_filter_metadata() -> Dict[str, Any]:
    """Provides dropdown sources for channels, countries, platforms, courses, and ad hierarchy."""
    data = get_raw_seed_data()
    meta = data["meta"].copy()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta["lastUpdated"] = now_str

    channels = list(data["channels"])
    countries = list(data["countries"])
    platforms = list(data["platforms"])
    courses = list(data["courses"])
    campaigns = list(data["campaigns"])
    adsets = list(data["adsets"])
    ads = list(data["ads"])

    if check_db_connection():
        try:
            db_res = sql_engine.execute_query("SELECT NOW() as db_now, MAX(created_at) as max_lead FROM leads_contact_event_logs WHERE deleted_at IS NULL;", {})
            if db_res.get("success") and db_res.get("rows"):
                r = db_res["rows"][0]
                db_now = r.get("db_now") or now_str
                meta["lastUpdated"] = str(db_now).split(".")[0]

            # Fetch distinct campaigns from DB if available
            c_res = sql_engine.execute_query("SELECT DISTINCT campaign_name FROM facebookads WHERE campaign_name IS NOT NULL AND campaign_name <> '' ORDER BY campaign_name LIMIT 150;", {})
            if c_res.get("success") and c_res.get("rows"):
                live_camps = [{"id": r["campaign_name"], "name": r["campaign_name"], "channel": "Meta", "country": "All"} for r in c_res["rows"] if r.get("campaign_name")]
                if live_camps:
                    campaigns = live_camps

            country_res = sql_engine.execute_query("SELECT DISTINCT country_code FROM leads_contact_event_logs WHERE country_code IS NOT NULL AND country_code <> '' ORDER BY country_code;", {})
            if country_res.get("success") and country_res.get("rows"):
                live_countries = [r["country_code"] for r in country_res["rows"] if r.get("country_code")]
                if live_countries:
                    countries = live_countries
        except Exception:
            pass

    return {
        "meta": meta,
        "channels": channels,
        "countries": countries,
        "platforms": platforms,
        "courses": courses,
        "campaigns": campaigns,
        "adsets": adsets,
        "ads": ads,
        "cohort_options": ["Till date", "D0", "D1", "D2", "D3", "D7", "D14", "D21", "D30"],
        "slicer_options": [
            {"key": "date", "label": "Lead capture date"},
            {"key": "channel", "label": "Channel"},
            {"key": "platform", "label": "Platform"},
            {"key": "country", "label": "Country"},
            {"key": "course", "label": "Course"},
            {"key": "campaign", "label": "Campaign"},
            {"key": "adset", "label": "Ad set"},
            {"key": "ad", "label": "Ad"}
        ]
    }

