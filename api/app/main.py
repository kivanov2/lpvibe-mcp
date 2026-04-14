from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="LPVibe Platform API", version="0.1.0", lifespan=lifespan)
app.include_router(health.router, tags=["health"])
