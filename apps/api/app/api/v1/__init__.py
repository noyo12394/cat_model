from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import assistant, incidents, live, models, places, portfolio, risks, routes, scenarios, sources

api_router = APIRouter()
api_router.include_router(live.router)
api_router.include_router(places.router)
api_router.include_router(incidents.router)
api_router.include_router(routes.router)
api_router.include_router(scenarios.router)
api_router.include_router(portfolio.router)
api_router.include_router(assistant.router)
api_router.include_router(sources.router)
api_router.include_router(models.router)
api_router.include_router(risks.router)
