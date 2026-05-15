"""
EnterpriseIQ Backend — Auth & User Management Router
/v1/auth/* endpoints
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.auth import FirebaseUser, get_current_user, require_admin
from app.core.clients import FirestoreClient, get_firestore

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/v1/auth", tags=["Auth"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    uid: str
    email: str
    name: str
    workspace_id: Optional[str] = None
    roles: list[str] = ["viewer"]
    created_at: Optional[str] = None


class WorkspaceCreate(BaseModel):
    name: str
    description: str = ""


class WorkspaceResponse(BaseModel):
    workspace_id: str
    name: str
    description: str
    owner_uid: str
    created_at: str
    member_count: int = 1


class InviteRequest(BaseModel):
    email: str
    role: str = "viewer"


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=UserProfile, summary="Get current user profile")
async def get_profile(
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    doc = fs.get_document("users", user.uid)
    if not doc:
        # Auto-create profile on first login
        profile = {
            "uid": user.uid,
            "email": user.email,
            "name": user.name,
            "roles": ["viewer"],
            "created_at": datetime.utcnow().isoformat(),
        }
        fs.set_document("users", user.uid, profile)
        return UserProfile(**profile)
    return UserProfile(**doc)


@router.put("/profile", response_model=UserProfile, summary="Update user profile")
async def update_profile(
    updates: dict,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    allowed_fields = {"name", "preferences"}
    safe_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    fs.update_document("users", user.uid, safe_updates)
    doc = fs.get_document("users", user.uid)
    return UserProfile(**doc)


@router.get("/workspaces", summary="List workspaces for current user")
async def list_workspaces(
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    workspaces = fs.list_documents(
        "workspaces", filters=[("owner_uid", "==", user.uid)]
    )
    return {"workspaces": workspaces, "total": len(workspaces)}


@router.post("/workspaces", response_model=WorkspaceResponse, status_code=201, summary="Create a workspace")
async def create_workspace(
    body: WorkspaceCreate,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    import uuid
    workspace_id = str(uuid.uuid4())
    workspace = {
        "workspace_id": workspace_id,
        "name": body.name,
        "description": body.description,
        "owner_uid": user.uid,
        "created_at": datetime.utcnow().isoformat(),
        "member_count": 1,
        "members": {user.uid: "admin"},
    }
    fs.set_document("workspaces", workspace_id, workspace)
    # Link workspace to user
    fs.update_document("users", user.uid, {"workspace_id": workspace_id})
    logger.info("Workspace created", workspace_id=workspace_id, owner=user.uid)
    return WorkspaceResponse(**workspace)


@router.get("/workspaces/{workspace_id}", summary="Get workspace details")
async def get_workspace(
    workspace_id: str,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    ws = fs.get_document("workspaces", workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["owner_uid"] != user.uid and user.uid not in ws.get("members", {}):
        raise HTTPException(status_code=403, detail="Access denied")
    return ws


@router.post("/workspaces/{workspace_id}/invite", summary="Invite user to workspace")
async def invite_to_workspace(
    workspace_id: str,
    body: InviteRequest,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    ws = fs.get_document("workspaces", workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws["owner_uid"] != user.uid:
        raise HTTPException(status_code=403, detail="Only workspace owner can invite")
    # Store invitation
    invite = {
        "workspace_id": workspace_id,
        "invited_email": body.email,
        "role": body.role,
        "invited_by": user.uid,
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
    }
    import uuid
    fs.set_document("invitations", str(uuid.uuid4()), invite)
    return {"message": f"Invitation sent to {body.email}", "role": body.role}
