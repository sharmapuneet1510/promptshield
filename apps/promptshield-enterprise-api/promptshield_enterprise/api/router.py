"""
Main API router - assembles all v1 routes under /api/v1.
"""

from fastapi import APIRouter

from promptshield_enterprise.api.v1 import admin, analytics, policies, precheck, proxy
from promptshield_enterprise.api.v1.health import router as health_router

# Top-level router with /api prefix
api_router = APIRouter()

# Health checks at root level (no /api prefix for k8s probes)
api_router.include_router(health_router)

# v1 routes
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(precheck.router)
v1_router.include_router(proxy.router)
v1_router.include_router(analytics.router)
v1_router.include_router(policies.router)
v1_router.include_router(admin.router)

api_router.include_router(v1_router)
