from fastapi import APIRouter
from backend.app.services.mock_data import get_raw_seed_data
from typing import Dict, Any

router = APIRouter(prefix="/metadata", tags=["Metadata"])

@router.get("")
def get_filter_metadata() -> Dict[str, Any]:
    """Provides dropdown sources for channels, countries, platforms, courses, and ad hierarchy."""
    data = get_raw_seed_data()
    return {
        "meta": data["meta"],
        "channels": data["channels"],
        "countries": data["countries"],
        "platforms": data["platforms"],
        "courses": data["courses"],
        "campaigns": data["campaigns"],
        "adsets": data["adsets"],
        "ads": data["ads"],
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
