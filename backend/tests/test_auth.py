"""
Tests for Auth endpoints (/v1/auth/*)
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestAuthProfile:
    def test_get_profile_new_user(self, client, mock_firestore, mock_firebase_user):
        mock_firestore.get_document.return_value = None
        resp = client.get("/v1/auth/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["uid"] == "test-user-123"
        assert data["email"] == "test@enterpriseiq.com"
        mock_firestore.set_document.assert_called_once()

    def test_get_profile_existing_user(self, client, mock_firestore):
        mock_firestore.get_document.return_value = {
            "uid": "test-user-123",
            "email": "test@enterpriseiq.com",
            "name": "Test User",
            "roles": ["analyst"],
            "created_at": "2024-01-01",
        }
        resp = client.get("/v1/auth/profile")
        assert resp.status_code == 200
        assert resp.json()["roles"] == ["analyst"]


class TestWorkspaces:
    def test_create_workspace(self, client, mock_firestore):
        resp = client.post("/v1/auth/workspaces", json={
            "name": "Acme Analytics",
            "description": "Main workspace",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Acme Analytics"
        assert "workspace_id" in data
        assert data["owner_uid"] == "test-user-123"

    def test_list_workspaces(self, client, mock_firestore):
        mock_firestore.list_documents.return_value = [
            {
                "id": "ws1",
                "workspace_id": "ws1",
                "name": "WS1",
                "description": "",
                "owner_uid": "test-user-123",
                "created_at": "2024-01-01",
                "member_count": 1,
            }
        ]
        resp = client.get("/v1/auth/workspaces")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_workspace(self, client, mock_firestore):
        mock_firestore.get_document.return_value = {
            "workspace_id": "ws1",
            "name": "My WS",
            "owner_uid": "test-user-123",
            "members": {"test-user-123": "admin"},
            "created_at": "2024-01-01",
        }
        resp = client.get("/v1/auth/workspaces/ws1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "My WS"

    def test_get_workspace_not_found(self, client, mock_firestore):
        mock_firestore.get_document.return_value = None
        resp = client.get("/v1/auth/workspaces/missing")
        assert resp.status_code == 404

    def test_get_workspace_access_denied(self, client, mock_firestore):
        mock_firestore.get_document.return_value = {
            "workspace_id": "ws1",
            "name": "Other WS",
            "owner_uid": "other-user",
            "members": {},
        }
        resp = client.get("/v1/auth/workspaces/ws1")
        assert resp.status_code == 403

    def test_invite_to_workspace(self, client, mock_firestore):
        mock_firestore.get_document.return_value = {
            "workspace_id": "ws1",
            "owner_uid": "test-user-123",
        }
        resp = client.post("/v1/auth/workspaces/ws1/invite", json={
            "email": "colleague@company.com",
            "role": "analyst",
        })
        assert resp.status_code == 200
        assert "Invitation sent" in resp.json()["message"]
        mock_firestore.set_document.assert_called_once()
