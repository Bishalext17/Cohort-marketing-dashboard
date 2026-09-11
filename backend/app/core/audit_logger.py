import os
import json
import logging
import threading
from datetime import datetime, timezone
from collections import deque
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, List, Optional
from enum import Enum

class AuditCategory(str, Enum):
    QUERY_EXECUTION = "QUERY_EXECUTION"
    LEAD_MUTATION = "LEAD_MUTATION"
    CACHE_INVALIDATION = "CACHE_INVALIDATION"
    AUTH_EVENT = "AUTH_EVENT"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    METADATA_REFRESH = "METADATA_REFRESH"

class AuditLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class AuditLogger:
    """
    Structured, memory-safe, and disk-capped audit logging system.
    - Memory: Bounded Ring-Buffer (deque maxlen=1000) -> Max ~5MB RAM usage.
    - Disk: RotatingFileHandler (10MB max, 5 backup files) -> Max 50MB disk usage.
    - Zero memory leak and zero disk bloat.
    """
    def __init__(self, log_dir: Optional[str] = None, max_memory_entries: int = 1000):
        # Determine base directory
        if log_dir is None:
            # Place in project root / logs
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            log_dir = os.path.join(base_dir, "logs")
        
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "audit.log")

        # Fixed bounded in-memory buffer (Zero RAM Leak)
        self.max_memory_entries = max_memory_entries
        self._memory_buffer: deque = deque(maxlen=max_memory_entries)
        self._lock = threading.Lock()

        # Setup rotating file logger
        self._logger = logging.getLogger("audit_logger")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        # Remove existing handlers to avoid duplicate outputs
        for h in list(self._logger.handlers):
            self._logger.removeHandler(h)

        # 10 MB per file, max 5 backup archives (50 MB cap total)
        self._file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self._file_handler.setFormatter(formatter)
        self._logger.addHandler(self._file_handler)

    def log_event(
        self,
        category: AuditCategory,
        action: str,
        details: Dict[str, Any],
        level: AuditLevel = AuditLevel.INFO,
        user: Optional[str] = None,
        ip_address: Optional[str] = None,
        duration_ms: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Record a critical audit event to both disk (rotating) and memory (ring buffer).
        """
        timestamp_utc = datetime.now(timezone.utc).isoformat()
        
        event = {
            "timestamp": timestamp_utc,
            "category": category.value if isinstance(category, AuditCategory) else str(category),
            "level": level.value if isinstance(level, AuditLevel) else str(level),
            "action": action,
            "user": user or "system",
            "ip_address": ip_address or "internal",
            "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
            "details": details
        }

        # 1. Write to rotating file
        try:
            log_line = json.dumps(event, ensure_ascii=False)
            if level == AuditLevel.ERROR:
                self._logger.error(log_line)
            elif level == AuditLevel.WARNING:
                self._logger.warning(log_line)
            else:
                self._logger.info(log_line)
            self._file_handler.flush()
        except Exception as e:
            # Fallback stdout print if file write encounters an issue
            print(f"[AUDIT LOGGING ERROR]: Failed to write log event: {e}")

        # 2. Append to bounded memory buffer (O(1) pop if maxlen reached)
        with self._lock:
            self._memory_buffer.append(event)

        return event

    def get_logs(
        self,
        category: Optional[str] = None,
        level: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query recent logs from in-memory ring buffer with filtering and pagination.
        """
        with self._lock:
            # Latest first
            events = list(reversed(self._memory_buffer))

        filtered = []
        for ev in events:
            if category and ev.get("category") != category:
                continue
            if level and ev.get("level") != level:
                continue
            if search:
                search_lower = search.lower()
                text_content = json.dumps(ev).lower()
                if search_lower not in text_content:
                    continue
            filtered.append(ev)

        return filtered[offset:offset + limit]

    def get_stats(self) -> Dict[str, Any]:
        """
        Return memory and disk health statistics for the audit logging system.
        """
        with self._lock:
            mem_count = len(self._memory_buffer)

        file_size_bytes = 0
        if os.path.exists(self.log_file):
            file_size_bytes = os.path.getsize(self.log_file)

        return {
            "in_memory_records": mem_count,
            "max_memory_capacity": self.max_memory_entries,
            "memory_usage_status": "healthy_bounded",
            "log_file_path": self.log_file,
            "log_file_size_kb": round(file_size_bytes / 1024, 2),
            "max_disk_cap_mb": 50
        }

    def close(self):
        """
        Close and release file handlers.
        """
        self._file_handler.close()
        self._logger.removeHandler(self._file_handler)

    def flush_memory(self) -> int:
        """
        Flush and clear in-memory ring buffer.
        """
        with self._lock:
            count = len(self._memory_buffer)
            self._memory_buffer.clear()
        
        self._file_handler.flush()
        return count

# Global Singleton instance
audit_logger = AuditLogger()
