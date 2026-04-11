"""
RamyPulse FastAPI Entrypoint.
Exposes the RamyPulse core analytics engine as a REST API.
"""

import os
import sys

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the root project path is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routers import (  # noqa: E402
    admin,
    alerts,
    auth,
    campaigns,
    clients,
    dashboard,
    explorer,
    health,
    recommendations,
    social_metrics,
    watch_runs,
    watchlists,
)
from core.security.auth import get_current_client  # noqa: E402

app = FastAPI(
    title="RamyPulse Engine API",
    description="API REST pour la plateforme d'intelligence marketing RamyPulse",
    version="1.0.0",
)

# Enable CORS for the frontend (Google Labs Stitch / Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Redirecte la racine vers la documentation interactive."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/docs")


# --- Public routes (no auth) ---
app.include_router(health.router, prefix="/api")

# --- Protected routes (require X-API-Key) ---
_auth = [Depends(get_current_client)]
app.include_router(dashboard.router, prefix="/api", dependencies=_auth)
app.include_router(alerts.router, prefix="/api", dependencies=_auth)
app.include_router(watchlists.router, prefix="/api", dependencies=_auth)
app.include_router(watch_runs.router, prefix="/api", dependencies=_auth)
app.include_router(campaigns.router, prefix="/api", dependencies=_auth)
app.include_router(recommendations.router, prefix="/api", dependencies=_auth)
app.include_router(explorer.router, prefix="/api", dependencies=_auth)
app.include_router(social_metrics.router, prefix="/api", dependencies=_auth)
app.include_router(auth.router, prefix="/api", dependencies=_auth)
app.include_router(clients.router, prefix="/api", dependencies=_auth)

# --- Admin routes (no auth in this lot - will be added at integration) ---
app.include_router(admin.router, prefix="/api", dependencies=_auth)
