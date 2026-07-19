from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    assistant,
    cat_charts,
    catmodel,
    community,
    copilot,
    incidents,
    learn,
    live,
    models,
    places,
    portfolio,
    research,
    risks,
    roadmap,
    routes,
    scenarios,
    sources,
)

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
api_router.include_router(community.router)
api_router.include_router(catmodel.router)
api_router.include_router(cat_charts.router)
api_router.include_router(copilot.router)
api_router.include_router(learn.router)
api_router.include_router(research.router)
api_router.include_router(roadmap.router)
