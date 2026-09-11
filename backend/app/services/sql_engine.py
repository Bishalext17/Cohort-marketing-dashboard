import os
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text
from backend.app.core.database import engine, check_db_connection
from backend.app.core.config import settings
from backend.app.models.schemas import FilterParams
from backend.app.services.cache_manager import cache_manager
import logging

logger = logging.getLogger(__name__)

QUERIES_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "queries"
)

class SQLEngine:
    """
    Template compilation and execution engine for Metabase-style SQL queries.
    Supports:
      - Variable interpolation: {{cohort_days}}, {{from_date}}, {{to_date}}, {{slice_1}}, {{slice_2}}
      - Optional bracket clauses: [[AND ...]]
      - Parameterized execution with SQLAlchemy
    """

    def __init__(self, queries_dir: str = QUERIES_ROOT):
        self.queries_dir = queries_dir
        self._query_cache: Dict[str, Dict[str, Any]] = {}


    def get_query_files(self) -> List[Dict[str, str]]:
        """Lists all available SQL production and audit queries with category metadata."""
        files = []
        if not os.path.exists(self.queries_dir):
            return files

        for root, _, filenames in os.walk(self.queries_dir):
            for fn in sorted(filenames):
                if fn.endswith(".sql"):
                    rel_path = os.path.relpath(os.path.join(root, fn), self.queries_dir)
                    category = os.path.basename(root)
                    files.append({
                        "filename": fn,
                        "relative_path": rel_path.replace("\\", "/"),
                        "category": category,
                        "title": fn.replace(".sql", "").replace("_", " ").title()
                    })
        return files

    def read_query(self, relative_path: str) -> Optional[str]:
        """Reads the raw SQL query content."""
        target_path = os.path.join(self.queries_dir, relative_path)
        if not os.path.exists(target_path):
            return None
        with open(target_path, "r", encoding="utf-8") as f:
            return f.read()

    def compile_template(self, sql_template: str, params: Dict[str, Any]) -> str:
        """
        Compiles Metabase-style template into valid MySQL/MariaDB SQL.
        Handles optional blocks `[[ ... ]]` and variables `{{ ... }}`.
        """
        compiled = sql_template

        # 1. Process optional blocks: [[ AND column IN ({{var}}) ]]
        def replace_optional(match):
            block = match.group(1)
            # Find all {{var}} inside the optional block
            var_matches = re.findall(r"\{\{([a-zA-Z0-9_]+)\}\}", block)
            for var in var_matches:
                val = params.get(var)
                # If param is not provided or empty, drop the entire optional block
                if val is None or val == "" or val == [] or val == ["__EMPTY__"]:
                    return ""
            
            # If all variables exist, keep block and substitute variables
            result_block = block
            for var in var_matches:
                val = params.get(var)
                val_sql = self._format_sql_value(val)
                result_block = result_block.replace(f"{{{{{var}}}}}", val_sql)
            return result_block

        compiled = re.sub(r"\[\[(.*?)\]\]", replace_optional, compiled, flags=re.DOTALL)

        # 2. Process required variables outside optional blocks
        var_matches = re.findall(r"\{\{([a-zA-Z0-9_]+)\}\}", compiled)
        for var in var_matches:
            val = params.get(var)
            val_sql = self._format_sql_value(val)
            compiled = compiled.replace(f"{{{{{var}}}}}", val_sql)

        return compiled

    def _format_sql_value(self, val: Any) -> str:
        """Safely formats a parameter value for SQL interpolation."""
        if val is None:
            return "NULL"
        elif isinstance(val, bool):
            return "TRUE" if val else "FALSE"
        elif isinstance(val, (int, float)):
            return str(val)
        elif isinstance(val, list):
            if not val:
                return "NULL"
            escaped_items = [f"'{self._escape_string(str(item))}'" for item in val]
            return ", ".join(escaped_items)
        else:
            return f"'{self._escape_string(str(val))}'"

    def _escape_string(self, s: str) -> str:
        """Basic SQL string escaping to prevent syntax breakage."""
        return s.replace("'", "''").replace("\\", "\\\\")

    def execute_query(self, sql_template: str, params: Dict[str, Any], force_refresh: bool = False) -> Dict[str, Any]:
        """
        Compiles and executes SQL query against MariaDB.
        Returns rows, column names, execution duration in ms, and compiled SQL.
        """
        compiled_sql = self.compile_template(sql_template, params)
        start_time = time.time()

        # Strict Read-Only Safety Guard for Production Protection
        write_keywords = r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|REPLACE|CREATE|GRANT|REVOKE|LOCK)\b"
        if re.search(write_keywords, compiled_sql, re.IGNORECASE):
            logger.warning("Attempted write/mutation query blocked in read-only production mode.")
            return {
                "success": False,
                "executed": False,
                "error": "Security Restriction: Write / DDL operations are strictly disabled. The dashboard operates in READ-ONLY mode on the production database.",
                "compiled_sql": compiled_sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "duration_ms": 0.0
            }

        # Check In-Memory Query Cache First
        cache_key = f"sql:{compiled_sql}"
        if settings.CACHE_ENABLED and not force_refresh:
            cached_res = cache_manager.get(cache_key)
            if cached_res:
                logger.info("Serving SQL query results directly from cache_manager (0 DB load).")
                res = dict(cached_res)
                res["duration_ms"] = round((time.time() - start_time) * 1000, 2)
                res["cached"] = True
                return res

        if not check_db_connection() or not engine:
            return {
                "success": False,
                "executed": False,
                "error": "Live MariaDB database is currently disconnected. Running in fallback simulation mode.",
                "compiled_sql": compiled_sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "duration_ms": round((time.time() - start_time) * 1000, 2)
            }

        try:
            # Handle multi-statement files by taking the primary statement
            statements = [s.strip() for s in compiled_sql.split(";") if s.strip() and not all(line.strip().startswith("--") or line.strip().startswith("/*") for line in s.strip().splitlines())]
            exec_sql = statements[0] if statements else compiled_sql

            with engine.connect() as conn:
                result = conn.execute(text(exec_sql))
                columns = list(result.keys())
                raw_rows = result.fetchall()
                rows = [dict(zip(columns, row)) for row in raw_rows]
                duration_ms = round((time.time() - start_time) * 1000, 2)

                res = {
                    "success": True,
                    "executed": True,
                    "compiled_sql": compiled_sql,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "duration_ms": duration_ms,
                    "cached": False
                }
                
                if settings.CACHE_ENABLED:
                    cache_manager.set(cache_key, res)
                    
                return res
        except Exception as e:
            logger.error(f"SQL Execution error: {e}")
            return {
                "success": False,
                "executed": True,
                "error": str(e),
                "compiled_sql": compiled_sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "duration_ms": round((time.time() - start_time) * 1000, 2)
            }


sql_engine = SQLEngine()
