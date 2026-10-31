"""
FastAPI Main Application and Lifecycle Management.
Mounts all REST API routers, configures CORS, and serves React frontend.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.app.models.database import init_db
from backend.app.api.routes_recon import router as recon_router
from backend.app.api.routes_exceptions import router as exceptions_router
from backend.app.api.routes_audit import router as audit_router
from backend.app.api.routes_dashboard import router as dashboard_router
from backend.app.api.routes_reconops import router as reconops_router
from backend.app.api.routes_reports import router as reports_router
from backend.app.api.routes_files import router as files_router
from backend.data.sample_generator import generate_all_datasets, DATA_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB & Seed Data on startup
    init_db()
    if not os.path.exists(os.path.join(DATA_DIR, "internal_ledger_20260315.csv")):
        generate_all_datasets(scale_factor=0.04)
    yield


app = FastAPI(
    title="PayBridge Automated Reconciliation Engine",
    description="Production-grade multi-bank settlement and reconciliation platform (SWIFT MT940, ISO 20022 CAMT.053, CSV).",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for React UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routers
app.include_router(recon_router)
app.include_router(exceptions_router)
app.include_router(audit_router)
app.include_router(dashboard_router)
app.include_router(reconops_router)
app.include_router(reports_router)
app.include_router(files_router)


@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "Reconciliation Engine v1.0",
        "timestamp": "2026-03-30T10:00:00Z",
        "supported_formats": ["CSV", "SWIFT_MT940", "ISO20022_CAMT053"],
        "supported_banks": ["HDFC", "ICICI", "AXIS", "SBI", "KOTAK", "YESBANK", "INDUSIND"]
    }


# Mount built React frontend if dist exists
dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(dist_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(dist_path, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
