"""
RamyPulse FastAPI Entrypoint.
Exposes the RamyPulse core analytics engine as a REST API.
"""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure the root project path is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.routers import health, dashboard, alerts, watchlists, campaigns, recommendations, explorer, admin, social_metrics

app = FastAPI(
    title="RamyPulse Engine API",
    description="API REST pour la plateforme d'intelligence marketing RamyPulse",
    version="1.0.0"
)

# Enable CORS for the frontend (Google Labs Stitch / Vite)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root redirect to docs
@app.get("/")
def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(watchlists.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")
app.include_router(explorer.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(social_metrics.router, prefix="/api")
