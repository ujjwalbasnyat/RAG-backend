from fastapi import APIRouter

from app.api.v1.endpoints import chat, ingestion

api_router = APIRouter()
api_router.include_router(ingestion.router, tags=["ingestion"])
api_router.include_router(chat.router, tags=["chat"])
