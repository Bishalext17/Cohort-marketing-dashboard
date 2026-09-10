from fastapi import APIRouter, HTTPException
from typing import List
from backend.app.models.schemas import QueryFileItem, QueryRunRequest, QueryRunResponse
from backend.app.services.sql_engine import sql_engine

router = APIRouter(prefix="/queries", tags=["Query Studio"])

@router.get("", response_model=List[QueryFileItem])
def list_queries():
    """Lists all production and audit SQL queries."""
    return sql_engine.get_query_files()

@router.get("/template")
def get_query_template(path: str):
    """Retrieves the raw SQL content of a given query file."""
    content = sql_engine.read_query(path)
    if content is None:
        raise HTTPException(status_code=404, detail="Query template file not found.")
    return {"path": path, "sql": content}

@router.post("/run", response_model=QueryRunResponse)
def run_query(req: QueryRunRequest):
    """
    Compiles and executes SQL query against MariaDB or provides compiled preview in simulation mode.
    """
    raw_sql = req.custom_sql
    if not raw_sql and req.query_path:
        raw_sql = sql_engine.read_query(req.query_path)
        if raw_sql is None:
            raise HTTPException(status_code=404, detail=f"Query file {req.query_path} not found.")

    if not raw_sql:
        raise HTTPException(status_code=400, detail="Either query_path or custom_sql must be provided.")

    params = {
        "cohort_days": req.cohort_days,
        "from_date": req.from_date,
        "to_date": req.to_date,
        "campaign_nm": req.campaign_nm,
        "country_cd": req.country_cd,
        "ad_nm": req.ad_nm,
        "traffic": req.traffic,
        "synced_only": req.synced_only,
        "slice_1": req.slice_1,
        "slice_2": req.slice_2
    }

    result = sql_engine.execute_query(raw_sql, params)
    return QueryRunResponse(**result)
