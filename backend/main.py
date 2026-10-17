# D:\FYP\FORGE-1\backend\main.py
from contextlib import asynccontextmanager

import aiosqlite
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from agents.orchestrator import build_forge_graph
from agents.state import msgpack_allowlist
from backend.core.config import settings
from backend.routes import auth_router, chat_router, health_router, requests_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the checkpointer once, so paused runs survive a server restart (D-123)."""
    async with aiosqlite.connect(settings.CHECKPOINT_DB) as conn:
        saver = AsyncSqliteSaver(conn, serde=JsonPlusSerializer(allowed_msgpack_modules=msgpack_allowlist()))
        await saver.setup()
        app.state.forge_graph = build_forge_graph().compile(checkpointer=saver)
        yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Modular Conversational AI Agent for FORGE Website Builder Studio",
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

# Register API Routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(requests_router)
app.include_router(chat_router)   # old free chat, kept until the new clarification screen exists (D-137)

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
