"""
Production Reference Dataset and Seed Generator for Cohort Marketing Performance.
Contains the exact 2-fact-grain data:
1. Spend grain: (date, campaign, adset, ad) -> spend, impressions, clicks, pageviews, fb_results
2. Leads grain: lead-level records -> [booked_day_offset, scheduled_day_offset, attended_day_offset, converted_day_offset, revenue]
"""
from typing import Dict, Any, List
import datetime

def get_raw_seed_data() -> Dict[str, Any]:
    return {
        "meta": {
            "start": "2026-07-01",
            "days": 31,
            "lastUpdated": "2026-07-31T09:30:00+05:30"
        },
        "channels": ["Meta", "Google", "Others"],
        "countries": ["US", "UK", "CA", "IN"],
        "platforms": ["Facebook", "Instagram", "Others", "N/A"],
        "courses": [
            "Bhagavad Gita for Kids",
            "Spoken English",
            "Vedic Maths",
            "Coding for Kids",
            "Public Speaking",
            "Others"
        ],
        "campaigns": [
            {"id": "CMP1001", "name": "GE_Digi_CBO_Registration_US_Gita_15072026", "channel": "Meta", "country": "US"},
            {"id": "CMP1002", "name": "GE_Digi_ABO_Registration_UK_Gita_25072026", "channel": "Meta", "country": "UK"},
            {"id": "CMP1003", "name": "GE_ADV_IN_TopCreatives_Reg_Gita_08052026", "channel": "Meta", "country": "IN"},
            {"id": "CMP1004", "name": "GE_Digi_CBO_Registration_CA_Gita_01072026", "channel": "Meta", "country": "CA"},
            {"id": "CMP1005", "name": "GS_Search_Brand_US_Gita_2026", "channel": "Google", "country": "US"},
            {"id": "CMP1006", "name": "GS_PMax_Registration_IN_Gita_2026", "channel": "Google", "country": "IN"},
            {"id": "CMP1007", "name": "YT_Influencer_Bundle_US_Gita_Q3", "channel": "Others", "country": "US"},
            {"id": "CMP1008", "name": "GE_Digi_CBO_Registration_US_Gita_15072026", "channel": "Meta", "country": "US"}
        ],
        "adsets": [
            {"id": "AST2001", "name": "GE_Lookalike_1pct_2026", "campaign": 0},
            {"id": "AST2002", "name": "GE_Interest_Cohorts_2026", "campaign": 0},
            {"id": "AST2003", "name": "GE_Lookalike_1pct_2026", "campaign": 1},
            {"id": "AST2004", "name": "GE_Interest_Cohorts_2026", "campaign": 1},
            {"id": "AST2005", "name": "GE_Lookalike_1pct_2026", "campaign": 2},
            {"id": "AST2006", "name": "GE_Interest_Cohorts_2026", "campaign": 2},
            {"id": "AST2007", "name": "GE_Lookalike_1pct_2026", "campaign": 3},
            {"id": "AST2008", "name": "GE_Interest_Cohorts_2026", "campaign": 3},
            {"id": "AST2009", "name": "GS_Lookalike_1pct_2026", "campaign": 4},
            {"id": "AST2010", "name": "GS_Interest_Cohorts_2026", "campaign": 4},
            {"id": "AST2011", "name": "GS_Lookalike_1pct_2026", "campaign": 5},
            {"id": "AST2012", "name": "GS_Interest_Cohorts_2026", "campaign": 5},
            {"id": "AST2013", "name": "YT_Lookalike_1pct_a_Q3", "campaign": 6},
            {"id": "AST2014", "name": "GE_Lookalike_1pct_2026", "campaign": 7},
            {"id": "AST2015", "name": "GE_Interest_Cohorts_2026", "campaign": 7}
        ],
        "ads": [
            {"id": "AD3001", "name": "Creative_V1_Static_Lookalike_1pct", "adset": 0},
            {"id": "AD3002", "name": "Creative_V2_Video_Lookalike_1pct", "adset": 0},
            {"id": "AD3003", "name": "Creative_V1_Static_Interest_Cohorts", "adset": 1},
            {"id": "AD3004", "name": "Creative_V2_Video_Interest_Cohorts", "adset": 1},
            {"id": "AD3005", "name": "Creative_V1_Static_Lookalike_1pct", "adset": 2},
            {"id": "AD3006", "name": "Creative_V2_Video_Lookalike_1pct", "adset": 2},
            {"id": "AD3007", "name": "Creative_V1_Static_Interest_Cohorts", "adset": 3},
            {"id": "AD3008", "name": "Creative_V2_Video_Interest_Cohorts", "adset": 3},
            {"id": "AD3009", "name": "Creative_V1_Static_Lookalike_1pct", "adset": 4},
            {"id": "AD3010", "name": "Creative_V2_Video_Lookalike_1pct", "adset": 4},
            {"id": "AD3011", "name": "Creative_V1_Static_Interest_Cohorts", "adset": 5},
            {"id": "AD3012", "name": "Creative_V2_Video_Interest_Cohorts", "adset": 5},
            {"id": "AD3013", "name": "Creative_V1_Static_Lookalike_1pct", "adset": 6},
            {"id": "AD3014", "name": "Creative_V2_Video_Lookalike_1pct", "adset": 6},
            {"id": "AD3015", "name": "Creative_V1_Static_Interest_Cohorts", "adset": 7},
            {"id": "AD3016", "name": "Creative_V2_Video_Interest_Cohorts", "adset": 7},
            {"id": "AD3017", "name": "Creative_V1_Static_Lookalike_1pct", "adset": 8},
            {"id": "AD3018", "name": "Creative_V2_Video_Lookalike_1pct", "adset": 8},
            {"id": "AD3019", "name": "Creative_V1_Static_Interest_Cohorts", "adset": 9},
            {"id": "AD3020", "name": "Creative_V2_Video_Interest_Cohorts", "adset": 9},
            {"id": "AD3021", "name": "Creative_V1_Static_Lookalike_1pct", "adset": 10},
            {"id": "AD3022", "name": "Creative_V2_Video_Lookalike_1pct", "adset": 10},
            {"id": "AD3023", "name": "Creative_V1_Static_Interest_Cohorts", "adset": 11},
            {"id": "AD3024", "name": "Creative_V2_Video_Interest_Cohorts", "adset": 11},
            {"id": "AD3025", "name": "Creative_V1_Static_Lookalike_1pct", "adset": 12},
            {"id": "AD3026", "name": "Creative_V2_Video_Lookalike_1pct", "adset": 12},
            {"id": "AD3027", "name": "Creative_V1_Static_Lookalike_1pct", "adset": 13},
            {"id": "AD3028", "name": "Creative_V2_Video_Lookalike_1pct", "adset": 13},
            {"id": "AD3029", "name": "Creative_V1_Static_Interest_Cohorts", "adset": 14},
            {"id": "AD3030", "name": "Creative_V2_Video_Interest_Cohorts", "adset": 14}
        ],
        # [camp_idx, adset_idx, ad_idx, channel_idx, country_idx, platform_idx, course_idx]
        "combos": [
            [0,0,0,0,0,0,0],[0,0,1,0,0,1,0],[0,1,2,0,0,1,1],[0,1,3,0,0,0,1],
            [1,2,4,0,1,0,1],[1,2,5,0,1,1,1],[1,3,6,0,1,1,4],[1,3,7,0,1,0,4],
            [2,4,8,0,3,0,2],[2,4,9,0,3,2,2],[2,5,10,0,3,1,3],[2,5,11,0,3,2,3],
            [3,6,12,0,2,2,4],[3,6,13,0,2,1,4],[3,7,14,0,2,2,0],[3,7,15,0,2,0,0],
            [4,8,16,1,0,3,0],[4,8,17,1,0,3,0],[4,9,18,1,0,3,1],[4,9,19,1,0,3,1],
            [5,10,20,1,3,3,3],[5,10,21,1,3,3,3],[5,11,22,1,3,3,2],[5,11,23,1,3,3,2],
            [6,12,24,2,0,3,5],[6,12,25,2,0,3,5],[7,13,26,0,0,2,0],[7,13,27,0,0,1,0],
            [7,14,28,0,0,2,5],[7,14,29,0,0,0,5]
        ]
    }
