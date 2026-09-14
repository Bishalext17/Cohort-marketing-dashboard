from fastapi import APIRouter
from backend.app.services.campaign_tagger import campaign_tagger

router = APIRouter(tags=["Catalog & Metadata"])

@router.get("/catalog")
@router.get("/metadata/catalog")
async def get_catalog():
    """
    Catalog & Dimension Hierarchy Endpoint.
    Returns available periods, markets, courses, date bounds, and campaign tags.
    """
    dates = [f"2026-07-{str(i).zfill(2)}" for i in range(1, 32)]
    markets = ["India", "United States", "UAE", "Singapore", "United Kingdom", "BDG", "MEA", "INT"]
    courses = ["Public Speaking & Debating", "Creative Writing", "Young Authors Program", "Financial Literacy", "English", "Math/Science", "Gita"]

    hierarchy = []
    for norm_name, entry in campaign_tagger.name_map.items():
        hierarchy.append({
            "campaign": entry["display_name"],
            "campaign_id": entry.get("campaign_id") or norm_name[:12],
            "course": entry["course"],
            "country": entry["market"],
            "channel": entry["channel"]
        })

    return {
        "from": "2026-07-01",
        "to": "2026-07-31",
        "companyFrom": "2026-07-01",
        "companyTo": "2026-07-31",
        "extractedAt": "2026-07-31T09:30:00Z",
        "metaRetrievedAt": "2026-07-31T09:30:00Z",
        "outcomesThrough": "2026-07-31",
        "periods": ["D0", "D1", "D3", "D7", "D14", "D21", "D30", "Till date"],
        "options": {
            "date": dates,
            "country": markets,
            "course": courses,
            "channel": ["Meta", "Google", "Referral", "Other/Non-Meta"],
            "traffic": ["High-Intent", "Lookalike", "Broad", "Interest-Based"]
        },
        "markets": markets,
        "courses": courses,
        "hierarchy": hierarchy
    }
