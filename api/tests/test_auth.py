import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.auth import get_current_user, AuthUser
from app.config import settings

app = FastAPI()


@app.get("/protected")
async def protected(user: AuthUser = Depends(get_current_user)):
    return {"user_id": str(user.user_id), "github_login": user.github_login}


client = TestClient(app, raise_server_exceptions=False)


def _make_token(payload_overrides: dict | None = None, key: str | None = None) -> str:
    payload = {
        "user_id": str(uuid.uuid4()),
        "github_login": "testuser",
        "github_id": 12345,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    }
    if payload_overrides:
        payload.update(payload_overrides)
    return jwt.encode(payload, key or settings.jwt_signing_key, algorithm="HS256")


def test_valid_token():
    token = _make_token()
    resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["github_login"] == "testuser"


def test_missing_token():
    resp = client.get("/protected")
    assert resp.status_code == 401


def test_expired_token():
    token = _make_token({"exp": datetime.now(timezone.utc) - timedelta(hours=1)})
    resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_invalid_signature():
    token = _make_token(key="wrong-key")
    resp = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
