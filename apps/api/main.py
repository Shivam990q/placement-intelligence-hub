import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from packages.core.config import settings
from packages.core.database import init_db
from apps.api.routers import opportunities, approvals, sources, health
from apps.workers.ingestion_worker import IngestionWorker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database Tables
    await init_db()
    
    # Run an initial source discovery pass on startup
    try:
        asyncio.create_task(IngestionWorker.run_acquisition_cycle())
    except Exception as e:
        print(f"Initial acquisition error: {e}")
        
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-Source Placement Radar & Distribution Engine for Batch 2026/2027",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Mount Routers
app.include_router(health.router)
app.include_router(opportunities.router)
app.include_router(approvals.router)
app.include_router(sources.router)

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_file = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Web Dashboard not found"}

@app.get("/miniapp", response_class=HTMLResponse)
async def serve_miniapp():
    miniapp_file = os.path.join(WEB_DIR, "miniapp.html")
    if os.path.exists(miniapp_file):
        return FileResponse(miniapp_file)
    return {"message": "Telegram Mini App view not found"}

@app.post("/api/auth/telegram-verify")
async def verify_telegram_auth(payload: dict):
    from packages.security.telegram_auth import verify_telegram_init_data
    init_data = payload.get("init_data", "")
    auth_result = verify_telegram_init_data(init_data, settings.TELEGRAM_BOT_TOKEN)
    if not auth_result:
        return {"authenticated": False, "error": "Invalid or expired Telegram signature"}
    return {"authenticated": True, "user": auth_result.get("user")}

@app.get("/api")
async def api_root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "status": "online"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
