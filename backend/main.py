# D:\FYP\FORGE-1\backend\main.py
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents import file_store, preview
from agents.orchestrator import build_forge_graph
from backend.core.body_limit import BodySizeLimit
from backend.core.config import ROOT_DIR, settings
from backend.db.checkpoints import open_checkpointer
from backend.db.session import app_sessionmaker
from backend.routes import auth_router, health_router, projects_router, requests_router
from backend.routes.requests import repair_statuses
from backend.routes.owner_data import router as owner_data_router
from backend.routes.site_data import router as site_data_router
from backend.services.generated_files import PostgresFileStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the checkpointer once, so runs survive restarts and redeploys (D-123, persistence plan)."""
    if not settings.SUPABASE_DB_URL:
        raise RuntimeError("SUPABASE_DB_URL is not set in FORGE-1/.env; runs are saved in the database.")
    store = PostgresFileStore(settings.SUPABASE_DB_URL)          # generated sites' files (D-234)
    file_store.use_store(store)
    try:
        async with open_checkpointer(settings.SUPABASE_DB_URL) as saver:
            app.state.forge_graph = build_forge_graph().compile(checkpointer=saver)
            async with app_sessionmaker()() as session:   # requests left on "processing" by a crash
                await repair_statuses(app.state.forge_graph, session, app)
            yield
    finally:
        preview.stop_all()                                         # live preview dev servers (D-240)
        store.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="FORGE: describe a website in plain words; FORGE clarifies it and plans the build.",
    lifespan=lifespan,
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Refuse oversized bodies before they are read (D-193)
app.add_middleware(BodySizeLimit)

# Register API Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(requests_router)
app.include_router(site_data_router)
app.include_router(owner_data_router)

if __name__ == "__main__":
    # psycopg (the checkpointer) cannot run on Windows' default ProactorEventLoop
    # Reload watches only the code: builds/ holds preview and gate folders linked to node_modules (D-240), where a
    # change must never restart the server in the middle of a build.
    code = [str(ROOT_DIR / "agents"), str(ROOT_DIR / "backend")]
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True, reload_dirs=code,
                loop="asyncio:SelectorEventLoop")
