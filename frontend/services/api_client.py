"""Thin HTTP client wrapping the backend FastAPI endpoints, so Streamlit
components never build request URLs themselves."""

from __future__ import annotations

import os

import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 600  # pipeline runs (clone, index, LLM calls, tests) can be slow


def load_repository(source: str) -> dict:
    resp = requests.post(f"{BACKEND_URL}/repository/load", json={"source": source}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def send_chat(session_id: str, message: str, branch: str = "swe-agent/auto-fix") -> dict:
    resp = requests.post(
        f"{BACKEND_URL}/chat",
        json={"session_id": session_id, "message": message, "branch": branch},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def analyze_repo(session_id: str, message: str = "") -> dict:
    resp = requests.post(
        f"{BACKEND_URL}/chat/analyze",
        json={"session_id": session_id, "message": message},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_patch(session_id: str) -> dict:
    resp = requests.get(f"{BACKEND_URL}/patch/{session_id}", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def push_patch(session_id: str, branch: str, confirm: bool) -> dict:
    resp = requests.post(
        f"{BACKEND_URL}/patch/push",
        json={"session_id": session_id, "branch": branch, "confirm": confirm},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_test_report(session_id: str) -> dict:
    resp = requests.get(f"{BACKEND_URL}/report/{session_id}/tests", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_impact_report(session_id: str) -> dict:
    resp = requests.get(f"{BACKEND_URL}/report/{session_id}/impact", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_repository_report(session_id: str) -> dict:
    resp = requests.get(f"{BACKEND_URL}/report/{session_id}/repository", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()
