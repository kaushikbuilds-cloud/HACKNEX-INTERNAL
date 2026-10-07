from __future__ import annotations

from fastapi import FastAPI

from backend.api import chat, patch, report, repository

app = FastAPI(title="AI Software Engineering Agent")

app.include_router(repository.router)
app.include_router(chat.router)
app.include_router(patch.router)
app.include_router(report.router)


@app.get("/health")
def health():
    return {"status": "ok"}
