"""Сборка роутера API v1."""

from fastapi import APIRouter

from app.api.v1.routes import auth, event_types, health, public

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(event_types.router)
api_router.include_router(public.router)
