from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .db import create_tables
from .routers import auth, catalog, conversations, actions, approvals, tickets, dev

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Agentic Bakery Pro - IT Helpdesk API",
    description="Guided, stateful, data-consistent autonomous IT helpdesk backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(conversations.router)
app.include_router(actions.router)
app.include_router(approvals.router)
app.include_router(tickets.router)
app.include_router(dev.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        create_tables()
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"⚠️  Database initialization error: {e}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Agentic Bakery Pro IT Helpdesk API",
        "version": "1.0.0",
        "demo_mode": settings.ALLOW_DEMO_LOGIN,
        "docs": "/docs",
        "health": "/api/dev/health"
    }


@app.get("/health")
async def health():
    """Simple health check"""
    return {"status": "ok", "service": "bakery_api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
