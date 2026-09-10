from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class FilterParams(BaseModel):
    cohort_period: str = Field("Till date", description="Cohort window: D0, D1, D2, D3, D7, D14, D21, D30, or 'Till date'")
    date_from: Optional[str] = Field(None, description="Start date YYYY-MM-DD")
    date_to: Optional[str] = Field(None, description="End date YYYY-MM-DD")
    channels: Optional[List[str]] = None
    platforms: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    courses: Optional[List[str]] = None
    campaign_ids: Optional[List[str]] = None
    campaign_names: Optional[List[str]] = None
    adset_ids: Optional[List[str]] = None
    adset_names: Optional[List[str]] = None
    ad_ids: Optional[List[str]] = None
    ad_names: Optional[List[str]] = None
    slicers: Optional[List[str]] = Field(default_factory=list, description="Group by dimensions e.g. ['date', 'campaign', 'adset', 'ad', 'country', 'course']")

class KPITile(BaseModel):
    key: str
    label: str
    value: str
    numeric_value: float
    description: str
    format_type: str = "number" # currency, percentage, number

class KPITilesResponse(BaseModel):
    spend: KPITile
    leads: KPITile
    cpl: KPITile
    demos_attended: KPITile
    attendance_pct: KPITile
    conversions: KPITile
    conversion_pct: KPITile
    revenue: KPITile
    arpu: KPITile
    roas: KPITile
    impressions: KPITile
    clicks: KPITile
    ctr: KPITile

class MaturityDay(BaseModel):
    date: str
    day_num: int
    status: str # "counted", "dropped", "outside"
    is_mature: bool
    leads_captured: int
    attended_count: int
    conversions_count: int
    revenue: float

class CohortMaturityResponse(BaseModel):
    selected_cohort: str
    refresh_date: str
    total_dates: int
    counted_dates: int
    dropped_dates: int
    note: str
    days: List[MaturityDay]

class CohortTableRow(BaseModel):
    dimensions: Dict[str, Any]
    # Fixed at D0
    spend: float
    impressions: int
    clicks: int
    contacts_registered: int
    ctr_pct: float
    cpl: float
    # Cohort-dependent
    demos_booked: int
    demos_scheduled: int
    demos_attended: int
    attendance_pct: float
    conversions: int
    conversion_pct: float
    new_revenue: float
    arpu: float
    roas: float

class CohortMasterResponse(BaseModel):
    headers: List[Dict[str, str]]
    rows: List[CohortTableRow]
    totals: CohortTableRow
    row_count: int
    applied_cohort: str
    applied_filters: Dict[str, Any]

class DeviceMetric(BaseModel):
    os: str # "iOS", "Android", "Desktop/Other"
    leads: int
    leads_share_pct: float
    booked: int
    booked_pct: float
    attended: int
    attended_pct: float
    conversions: int
    conversion_pct: float
    revenue: float
    arpu: float
    conversion_ratio_vs_android: float

class DeviceComparisonResponse(BaseModel):
    title: str
    summary_insight: str
    devices: List[DeviceMetric]

class FollowUpContact(BaseModel):
    lead_id: str
    phone: str
    parent_name: str
    lead_date: str
    course: str
    campaign_name: str
    os_family: str
    status: str
    attended: bool
    converted: bool
    amount: float
    days_since_lead: int
    followup_priority: str
    notes: Optional[str] = None

class FollowUpListResponse(BaseModel):
    category: str
    count: int
    total_potential_or_actual_revenue: float
    contacts: List[FollowUpContact]

class UpdateLeadStatusRequest(BaseModel):
    status: Optional[str] = None
    followup_priority: Optional[str] = None
    notes: Optional[str] = None

class QueryFileItem(BaseModel):
    filename: str
    relative_path: str
    category: str
    title: str

class QueryRunRequest(BaseModel):
    query_path: Optional[str] = None
    custom_sql: Optional[str] = None
    cohort_days: int = 9999
    from_date: str = "2026-07-01"
    to_date: str = "2026-07-31"
    campaign_nm: Optional[List[str]] = None
    country_cd: Optional[str] = None
    ad_nm: Optional[str] = None
    traffic: Optional[str] = None
    synced_only: Optional[str] = None
    slice_1: Optional[str] = "campaign"
    slice_2: Optional[str] = "none"

class QueryRunResponse(BaseModel):
    success: bool
    executed: bool
    error: Optional[str] = None
    compiled_sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    duration_ms: float

