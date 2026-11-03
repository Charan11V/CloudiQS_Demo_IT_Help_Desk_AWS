"""Main FastAPI application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import (
    actions,
    admin,
    agentcore_bridge,
    analytics,
    approvals,
    auth,
    conversations,
    dev,
    devices,
    evaluations,
    health,
    knowledge,
    notifications,
    security,
    tickets,
    workspace,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="HELIO Agent API",
    description="Autonomous IT Operations Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://web:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (
    auth,
    health,
    workspace,
    conversations,
    tickets,
    actions,
    approvals,
    admin,
    analytics,
    devices,
    knowledge,
    security,
    notifications,
    evaluations,
    dev,
    agentcore_bridge,
):
    app.include_router(r.router)


@app.get("/")
async def root():
    from app.agentcore.client import agentcore_configured
    from app.config import AGENTCORE_RUNTIME_ARN

    return {
        "service": "HELIO Agent API",
        "version": "1.0.0",
        "status": "operational",
        "synthetic_data": True,
        "agentcore_runtime": agentcore_configured(),
        "agentcore_runtime_configured": bool(AGENTCORE_RUNTIME_ARN),
    }


@app.get("/health")
async def health_alias():
    return {"ok": True, "service": "agent-api"}
