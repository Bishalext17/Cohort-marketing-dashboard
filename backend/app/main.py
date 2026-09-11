import os
import sys

# Ensure root and backend directories are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)
for p in [root_dir, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.app.core.config import settings
from backend.app.core.database import check_db_connection
from backend.app.api.v1.router import api_v1_router
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cohort_dashboard")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

from backend.app.core.database import check_db_connection, get_db_status

@app.get("/health")
def health_check():
    db_stat = get_db_status()
    db_ok = db_stat.get("connected", False)
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "database_connected": db_ok,
        "engine_mode": "live_mariadb" if db_ok else "fallback_analytical_service",
        "database_status": db_stat
    }

# Frontend Static Files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_frontend_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
