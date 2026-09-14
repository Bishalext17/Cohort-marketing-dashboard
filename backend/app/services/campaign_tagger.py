import os
import csv
import re
from typing import Dict, Optional, Any

class CampaignTagger:
    """
    Authoritative Campaign Tagging & Governance Service.
    Resolves raw campaign names and platform IDs to:
    - Canonical Display Name
    - Course
    - Target Market
    - Channel
    - Tag Source

    Strict Contract:
    1. Exact matching after case/whitespace/punctuation normalization.
    2. Explicit aliases resolution.
    3. Unmatched entries are categorized strictly as 'Unmapped' (never silently 'Others').
    """

    def __init__(self, csv_path: Optional[str] = None):
        if not csv_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(base_dir, "data", "campaign-tags.csv")
        self.csv_path = csv_path
        self.name_map: Dict[str, Dict[str, Any]] = {}
        self.id_map: Dict[str, Dict[str, Any]] = {}
        self.load_registry()

    @staticmethod
    def normalize_key(text: str) -> str:
        if not text:
            return ""
        # Lowercase, strip leading/trailing, collapse multi-spaces and underscores
        cleaned = re.sub(r'[\s_\-]+', ' ', str(text).strip().lower())
        return cleaned

    def load_registry(self):
        if not os.path.exists(self.csv_path):
            return

        with open(self.csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                campaign = row.get("Campaign", "").strip()
                display_name = row.get("Display name", "").strip() or campaign
                course = row.get("Course", "").strip() or "Others"
                market = row.get("Market", "").strip() or "Others"
                channel = row.get("Channel", "").strip() or "Other/Non-Meta"
                tag_source = row.get("Tag source", "").strip() or "registry"
                campaign_id = row.get("Campaign ID", "").strip()
                aliases_raw = row.get("Aliases", "").strip()

                tag_entry = {
                    "raw_campaign": campaign,
                    "display_name": display_name,
                    "course": course,
                    "market": market,
                    "channel": channel,
                    "tag_source": tag_source,
                    "campaign_id": campaign_id
                }

                if campaign:
                    norm = self.normalize_key(campaign)
                    self.name_map[norm] = tag_entry

                if campaign_id:
                    self.id_map[campaign_id.strip()] = tag_entry

                if aliases_raw:
                    for alias in aliases_raw.split("|"):
                        if alias.strip():
                            self.name_map[self.normalize_key(alias.strip())] = tag_entry

    def resolve(self, campaign_name: Optional[str] = None, campaign_id: Optional[str] = None) -> Dict[str, Any]:
        # 1. Match by normalized campaign name
        if campaign_name:
            norm = self.normalize_key(campaign_name)
            if norm in self.name_map:
                return self.name_map[norm]

        # 2. Match by Campaign ID
        if campaign_id and str(campaign_id).strip() in self.id_map:
            return self.id_map[str(campaign_id).strip()]

        # 3. Direct / Organic Web Recognition
        if campaign_name:
            c_low = str(campaign_name).lower()
            if "parent.bambinos.live" in c_low or "bambinos.live/signup" in c_low or c_low.strip() in ["direct", "organic", "website"]:
                return {
                    "raw_campaign": campaign_name,
                    "display_name": "Direct Web Signup",
                    "course": "Direct Signups",
                    "market": "India",
                    "channel": "Direct / Organic Web",
                    "tag_source": "domain_resolver",
                    "campaign_id": campaign_id or ""
                }

        # 4. Fallback: Strict Unmapped
        return {
            "raw_campaign": campaign_name or "Unknown",
            "display_name": campaign_name or "Unmapped",
            "course": "Unmapped",
            "market": "Unmapped",
            "channel": "Unmapped",
            "tag_source": "unmapped",
            "campaign_id": campaign_id or ""
        }

campaign_tagger = CampaignTagger()
