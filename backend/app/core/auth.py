"""
EnterpriseIQ Backend — Firebase Auth Middleware
Validates Firebase ID tokens on every protected endpoint.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Optional

import firebase_admin
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# ── Initialise Firebase Admin SDK once ──────────────────────────────────────

_firebase_app: Optional[firebase_admin.App] = None


def _init_firebase() -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    cred_obj: Optional[credentials.Base] = None

    # Option 1: service account file path
    if settings.firebase_service_account_path and os.path.isfile(
        settings.firebase_service_account_path
    ):
        cred_obj = credentials.Certificate(settings.firebase_service_account_path)
        logger.info("Firebase: loaded credentials from file")

    # Option 2: base64-encoded JSON in env var
    elif settings.firebase_service_account_b64:
        raw = base64.b64decode(settings.firebase_service_account_b64)
        cred_dict = json.loads(raw)
        cred_obj = credentials.Certificate(cred_dict)
        logger.info("Firebase: loaded credentials from env var (b64)")

    # Option 3: Application Default Credentials
    else:
        cred_obj = credentials.ApplicationDefault()
        logger.info("Firebase: using Application Default Credentials")

    _firebase_app = firebase_admin.initialize_app(
        cred_obj,
        {"projectId": settings.firebase_project_id},
    )
    return _firebase_app


try:
    _init_firebase()
except Exception as exc:  # pragma: no cover
    logger.warning("Firebase init failed (running in dev/test mode)", error=str(exc))


# ── Bearer token extractor ──────────────────────────────────────────────────

_bearer = HTTPBearer(auto_error=False)


class FirebaseUser:
    """Decoded Firebase token payload."""

    def __init__(self, token_data: dict) -> None:
        self.uid: str = token_data.get("uid", "")
        self.email: str = token_data.get("email", "")
        self.name: str = token_data.get("name", "")
        self.workspace_id: Optional[str] = token_data.get("workspace_id")
        self.roles: list[str] = token_data.get("roles", ["viewer"])
        self.raw: dict = token_data

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles

    @property
    def is_analyst(self) -> bool:
        return "analyst" in self.roles or self.is_admin


async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> FirebaseUser:
    """FastAPI dependency — verify Firebase JWT and return FirebaseUser."""
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = creds.credentials
    try:
        decoded = auth.verify_id_token(token)
        return FirebaseUser(decoded)
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except auth.InvalidIdTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        logger.error("Token verification failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token verification failed"
        )


# ── Role-based guards ────────────────────────────────────────────────────────

def require_admin(user: FirebaseUser = Depends(get_current_user)) -> FirebaseUser:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def require_analyst(user: FirebaseUser = Depends(get_current_user)) -> FirebaseUser:
    if not user.is_analyst:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Analyst role required")
    return user
