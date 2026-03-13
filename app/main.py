from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.db import base  # noqa: F401


app = FastAPI(
    title="NovaMusic API",
    version="1.0.0",
    description="API para NovaMusic - app de música estilo Spotify",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "NovaMusic API running",
        "docs": "/docs",
        "api_version": "v1",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


