"""Tier 1 Authentication and Authorization Verification Tests for CrimeGraph AI.

Tests:
1. Valid user login (Analyst & Admin)
2. Invalid user login (wrong password / non-existent user)
3. Missing authentication token in strict mode
4. Expired authentication token handling
5. Malformed / corrupted token handling
6. Analyst role access permissions (read, investigate, create manual entity)
7. Admin role access permissions (user management + all analyst features)
8. Role enforcement / unauthorized access (Analyst attempting Admin routes -> 403)
9. Protected dataset immutability across roles (DELETE dataset entity -> 403)
10. AI Investigator authentication & authorization enforcement
11. Public health & root endpoint access without authentication
12. User store persistence isolation from synthetic_data.json
13. Token profile verification (GET /api/auth/me)
"""

import hashlib
import json
import os
import tempfile
from datetime import timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from crimegraph.api.app import create_app
from crimegraph.auth.models import UserRole
from crimegraph.auth.security import create_access_token, hash_password, verify_password
from crimegraph.auth.store import UserStore
from crimegraph.data.loader import get_default_dataset_path


def compute_sha256(filepath: Path) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestTier1Auth:

    @pytest.fixture(autouse=True)
    def setup_auth_environment(self, monkeypatch):
        """Isolates user store and manual data storage during testing."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_users:
            self.temp_users_path = Path(tf_users.name)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf_manual:
            self.temp_manual_path = Path(tf_manual.name)

        monkeypatch.setenv("CRIMEGRAPH_USERS_PATH", str(self.temp_users_path))
        monkeypatch.setenv("CRIMEGRAPH_MANUAL_DATA_PATH", str(self.temp_manual_path))
        monkeypatch.setenv("CRIMEGRAPH_JWT_SECRET", "test-secret-key-tier1-auth-2026")
        monkeypatch.setenv("CRIMEGRAPH_ANALYST_PASSWORD", "analyst@2026")
        monkeypatch.setenv("CRIMEGRAPH_ADMIN_PASSWORD", "admin@2026")

        yield

        if self.temp_users_path.exists():
            try:
                self.temp_users_path.unlink()
            except OSError:
                pass
        if self.temp_manual_path.exists():
            try:
                self.temp_manual_path.unlink()
            except OSError:
                pass

    def test_01_valid_login_analyst_and_admin(self):
        """TEST 1: Valid credentials return 200 OK, JWT Bearer token, and user profile."""
        app = create_app()
        client = TestClient(app)

        # Login Analyst
        res_a = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert "access_token" in data_a
        assert data_a["token_type"] == "bearer"
        assert data_a["user"]["username"] == "analyst"
        assert data_a["user"]["role"] == "ANALYST"

        # Login Admin
        res_adm = client.post("/api/auth/login", json={"username": "admin", "password": "admin@2026"})
        assert res_adm.status_code == 200
        data_adm = res_adm.json()
        assert data_adm["user"]["role"] == "ADMIN"

    def test_02_invalid_login_credentials(self):
        """TEST 2: Invalid password or non-existent username returns 401 Unauthorized."""
        app = create_app()
        client = TestClient(app)

        # Wrong password
        res_wp = client.post("/api/auth/login", json={"username": "analyst", "password": "wrong_password"})
        assert res_wp.status_code == 401
        assert "Invalid username or password" in res_wp.json()["detail"]

        # Non-existent user
        res_nu = client.post("/api/auth/login", json={"username": "ghost_user", "password": "password123"})
        assert res_nu.status_code == 401

    def test_03_missing_token_in_strict_mode(self, monkeypatch):
        """TEST 3: Unauthenticated request in strict mode returns 401 Unauthorized."""
        monkeypatch.setenv("CRIMEGRAPH_AUTH_STRICT", "true")
        app = create_app()
        client = TestClient(app)

        res = client.get("/api/graph")
        assert res.status_code == 401
        assert "Authentication required" in res.json()["detail"]

    def test_04_expired_token_handling(self, monkeypatch):
        """TEST 4: Request with expired JWT token returns 401 Unauthorized."""
        app = create_app()
        client = TestClient(app)

        # Create expired token (-10 seconds)
        expired_token, _ = create_access_token(
            username="analyst",
            role=UserRole.ANALYST,
            expires_delta=timedelta(seconds=-10)
        )

        headers = {"Authorization": f"Bearer {expired_token}"}
        res = client.get("/api/graph", headers=headers)
        assert res.status_code == 401
        assert "expired" in res.json()["detail"].lower()

    def test_05_malformed_token_handling(self):
        """TEST 5: Request with malformed or tampered token returns 401 Unauthorized."""
        app = create_app()
        client = TestClient(app)

        headers = {"Authorization": "Bearer not.a.valid.jwt.token"}
        res = client.get("/api/graph", headers=headers)
        assert res.status_code == 401
        assert "Authentication failed" in res.json()["detail"]

    def test_06_analyst_role_access_and_crud(self):
        """TEST 6: Authenticated Analyst can read graph, create manual entities, and investigate."""
        app = create_app()
        client = TestClient(app)

        login_res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Read Graph
        assert client.get("/api/graph", headers=headers).status_code == 200

        # 2. Create Manual Entity
        res_e = client.post("/api/entities", headers=headers, json={
            "entity_type": "PERSON",
            "name": "Target Suspect X"
        })
        assert res_e.status_code == 201
        ent_id = res_e.json()["id"]

        # 3. Create Manual Relationship
        res_r = client.post("/api/relationships", headers=headers, json={
            "source_id": "PERSON_017",
            "target_id": ent_id,
            "relationship": "KNOWS",
            "confidence": 0.92
        })
        assert res_r.status_code == 201

        # 4. Run AI Investigation
        res_ai = client.post("/api/investigate", headers=headers, json={
            "question": f"How is PERSON_017 connected to {ent_id}?"
        })
        assert res_ai.status_code == 200
        assert "PERSON_017" in res_ai.json()["path"]

    def test_07_admin_role_user_management(self):
        """TEST 7: Admin role can list and create user accounts."""
        app = create_app()
        client = TestClient(app)

        # Login Admin
        login_res = client.post("/api/auth/login", json={"username": "admin", "password": "admin@2026"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # List Users
        res_list = client.get("/api/auth/users", headers=headers)
        assert res_list.status_code == 200
        users = res_list.json()
        assert any(u["username"] == "admin" for u in users)

        # Create New User Account
        res_create = client.post("/api/auth/users", headers=headers, json={
            "username": "junior_analyst",
            "password": "SecurePassword123!",
            "full_name": "Junior Intelligence Analyst",
            "role": "ANALYST"
        })
        assert res_create.status_code == 201
        assert res_create.json()["username"] == "junior_analyst"

        # Verify new user can log in
        login_new = client.post("/api/auth/login", json={"username": "junior_analyst", "password": "SecurePassword123!"})
        assert login_new.status_code == 200

    def test_08_analyst_cannot_access_admin_routes(self):
        """TEST 8: Analyst attempting Admin-only endpoints receives 403 Forbidden."""
        app = create_app()
        client = TestClient(app)

        login_res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Analyst attempts GET /api/auth/users -> 403
        res_users = client.get("/api/auth/users", headers=headers)
        assert res_users.status_code == 403
        assert "Insufficient permissions" in res_users.json()["detail"]

        # Analyst attempts POST /api/auth/users -> 403
        res_create = client.post("/api/auth/users", headers=headers, json={
            "username": "rogue_user",
            "password": "password123"
        })
        assert res_create.status_code == 403

    def test_09_protected_dataset_immutability_enforced(self):
        """TEST 9: Protected dataset entities cannot be deleted even by Admin."""
        app = create_app()
        client = TestClient(app)

        login_adm = client.post("/api/auth/login", json={"username": "admin", "password": "admin@2026"})
        token_adm = login_adm.json()["access_token"]
        headers = {"Authorization": f"Bearer {token_adm}"}

        # Attempt to delete dataset suspect PERSON_017
        res_del = client.delete("/api/entities/PERSON_017", headers=headers)
        assert res_del.status_code == 403
        assert "Protected dataset entity cannot be deleted" in res_del.json()["detail"]

    def test_10_ai_investigator_auth_enforcement(self, monkeypatch):
        """TEST 10: AI Investigator requires valid authentication in strict mode."""
        monkeypatch.setenv("CRIMEGRAPH_AUTH_STRICT", "true")
        app = create_app()
        client = TestClient(app)

        # Unauthenticated query -> 401
        res_unauth = client.post("/api/investigate", json={"question": "Who are the suspects in Case 101?"})
        assert res_unauth.status_code == 401

        # Authenticated query -> 200 OK
        login_res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
        res_auth = client.post("/api/investigate", headers=headers, json={"question": "Who are the suspects in Case 101?"})
        assert res_auth.status_code == 200
        assert "PERSON_017" in res_auth.json()["answer"]

    def test_11_health_and_root_endpoints_remain_public(self, monkeypatch):
        """TEST 11: GET /api/health and GET / remain publicly accessible without auth for monitoring."""
        monkeypatch.setenv("CRIMEGRAPH_AUTH_STRICT", "true")
        app = create_app()
        client = TestClient(app)

        assert client.get("/api/health").status_code == 200
        assert client.get("/").status_code == 200

    def test_12_dataset_immutability_and_user_storage_isolation(self):
        """TEST 12: User management operations do not touch data/synthetic_data.json."""
        dataset_path = get_default_dataset_path()
        hash_before = compute_sha256(dataset_path)

        app = create_app()
        client = TestClient(app)

        # Login admin and create user
        login_adm = client.post("/api/auth/login", json={"username": "admin", "password": "admin@2026"})
        headers = {"Authorization": f"Bearer {login_adm.json()['access_token']}"}
        client.post("/api/auth/users", headers=headers, json={
            "username": "persistence_probe_user",
            "password": "Password123!",
            "role": "ANALYST"
        })

        hash_after = compute_sha256(dataset_path)
        assert hash_before == hash_after, "data/synthetic_data.json was modified by user operations!"

        # Verify users persisted in isolated users.json
        assert self.temp_users_path.exists()
        with open(self.temp_users_path, "r", encoding="utf-8") as f:
            u_data = json.load(f)
        assert any(u["username"] == "persistence_probe_user" for u in u_data.get("users", []))

    def test_13_get_current_user_profile(self):
        """TEST 13: GET /api/auth/me returns authenticated user details."""
        app = create_app()
        client = TestClient(app)

        login_res = client.post("/api/auth/login", json={"username": "analyst", "password": "analyst@2026"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res_me = client.get("/api/auth/me", headers=headers)
        assert res_me.status_code == 200
        data_me = res_me.json()
        assert data_me["username"] == "analyst"
        assert data_me["role"] == "ANALYST"
        assert "hashed_password" not in data_me
