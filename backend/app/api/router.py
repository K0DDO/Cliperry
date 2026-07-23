"""Aggregate API router."""

from fastapi import APIRouter

from app.api import analyze, download, files, history, tasks, worker

api_router = APIRouter()
api_router.include_router(analyze.router)
api_router.include_router(download.router)
api_router.include_router(files.router)
api_router.include_router(history.router)
api_router.include_router(tasks.router)
api_router.include_router(worker.router)
