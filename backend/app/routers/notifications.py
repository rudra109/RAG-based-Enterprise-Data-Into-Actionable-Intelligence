"""
EnterpriseIQ Backend — Notifications Router
/v1/notifications/* + WebSocket /ws/events
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Set

import structlog
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.auth import FirebaseUser, get_current_user
from app.core.clients import FirestoreClient, get_firestore

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Notifications"])

# ── WebSocket Connection Manager ─────────────────────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections per user."""

    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, user_id: str) -> None:
        await ws.accept()
        self._connections.setdefault(user_id, set()).add(ws)
        logger.info("WebSocket connected", user_id=user_id)

    def disconnect(self, ws: WebSocket, user_id: str) -> None:
        if user_id in self._connections:
            self._connections[user_id].discard(ws)
        logger.info("WebSocket disconnected", user_id=user_id)

    async def send_to_user(self, user_id: str, message: dict) -> None:
        dead: List[WebSocket] = []
        for ws in self._connections.get(user_id, set()):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[user_id].discard(ws)

    async def broadcast(self, message: dict) -> None:
        for user_id, connections in list(self._connections.items()):
            await self.send_to_user(user_id, message)


ws_manager = ConnectionManager()


# ── Schemas ──────────────────────────────────────────────────────────────────

class NotificationPrefs(BaseModel):
    anomaly_alerts: bool = True
    pipeline_alerts: bool = True
    forecast_ready: bool = True
    email_notifications: bool = False
    email_address: Optional[str] = None


class NotificationResponse(BaseModel):
    notification_id: str
    event_type: str
    title: str
    message: str
    severity: Optional[str] = None
    created_at: str
    read: bool = False
    metadata: dict = {}


# ── REST Endpoints ───────────────────────────────────────────────────────────

@router.get("/v1/notifications", response_model=List[NotificationResponse], summary="List notifications for current user")
async def list_notifications(
    limit: int = 50,
    unread_only: bool = False,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    filters = [("user_id", "==", user.uid)]
    if unread_only:
        filters.append(("read", "==", False))
    notifs = fs.list_documents("notifications", filters=filters)
    notifs = sorted(notifs, key=lambda x: x.get("created_at", ""), reverse=True)[:limit]
    return [NotificationResponse(**n) for n in notifs]


@router.post("/v1/notifications/{notification_id}/read", summary="Mark notification as read")
async def mark_read(
    notification_id: str,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    notif = fs.get_document("notifications", notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.get("user_id") != user.uid:
        raise HTTPException(status_code=403, detail="Access denied")
    fs.update_document("notifications", notification_id, {"read": True})
    return {"message": "Marked as read", "notification_id": notification_id}


@router.post("/v1/notifications/read-all", summary="Mark all notifications as read")
async def mark_all_read(
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    notifs = fs.list_documents("notifications", filters=[("user_id", "==", user.uid), ("read", "==", False)])
    for n in notifs:
        fs.update_document("notifications", n["id"], {"read": True})
    return {"message": f"Marked {len(notifs)} notifications as read"}


@router.get("/v1/notifications/preferences", response_model=NotificationPrefs, summary="Get notification preferences")
async def get_prefs(
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    doc = fs.get_document("notification_prefs", user.uid)
    if not doc:
        default = NotificationPrefs()
        fs.set_document("notification_prefs", user.uid, default.model_dump())
        return default
    return NotificationPrefs(**doc)


@router.put("/v1/notifications/preferences", response_model=NotificationPrefs, summary="Update notification preferences")
async def update_prefs(
    prefs: NotificationPrefs,
    user: FirebaseUser = Depends(get_current_user),
    fs: FirestoreClient = Depends(get_firestore),
):
    fs.set_document("notification_prefs", user.uid, prefs.model_dump())
    return prefs


# ── WebSocket Endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/events")
async def websocket_events(ws: WebSocket):
    """
    Real-time event stream over WebSocket.
    Client must send: {"token": "<Firebase ID token>"}
    """
    await ws.accept()

    # First message must be authentication
    try:
        auth_msg = await asyncio.wait_for(ws.receive_json(), timeout=10.0)
    except asyncio.TimeoutError:
        await ws.close(code=4001, reason="Auth timeout")
        return

    token = auth_msg.get("token", "")
    try:
        from firebase_admin import auth
        decoded = auth.verify_id_token(token)
        user_id = decoded["uid"]
    except Exception:
        await ws.close(code=4003, reason="Invalid token")
        return

    # Re-register with auth confirmed
    await ws.close()  # close the auto-accepted one

    # Actually manage with proper connect
    await ws_manager.connect(ws, user_id)
    await ws.send_json({"type": "connected", "user_id": user_id, "timestamp": datetime.utcnow().isoformat()})

    try:
        while True:
            data = await ws.receive_json()
            # Echo ping/pong
            if data.get("type") == "ping":
                await ws.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        ws_manager.disconnect(ws, user_id)


# ── Internal helper (called by Pub/Sub push subscription handler) ─────────────

async def push_notification_to_user(user_id: str, event: dict, fs: FirestoreClient) -> None:
    """Store notification in Firestore and push to WebSocket."""
    import uuid

    notification_id = str(uuid.uuid4())
    notif = {
        "notification_id": notification_id,
        "user_id": user_id,
        "event_type": event.get("event_type", ""),
        "title": event.get("title", "New Event"),
        "message": event.get("message", ""),
        "severity": event.get("severity"),
        "created_at": datetime.utcnow().isoformat(),
        "read": False,
        "metadata": event.get("metadata", {}),
    }
    fs.set_document("notifications", notification_id, notif)
    await ws_manager.send_to_user(user_id, {"type": "notification", **notif})
