"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient


class TestAuthRegister:
    """Tests for POST /auth/register."""

    async def test_register_first_user_bootstrap(self, client: AsyncClient):
        """First user can register without authentication."""
        resp = await client.post(
            "/auth/register",
            json={"username": "firstadmin", "password": "secret123", "rol": "admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["username"] == "firstadmin"
        assert data["rol"] == "admin"

    async def test_register_subsequent_requires_admin(self, client: AsyncClient, admin_headers):
        """Subsequent users require admin authentication."""
        # First create admin user
        await client.post(
            "/auth/register",
            json={"username": "admin2", "password": "secret123", "rol": "admin"},
            headers=admin_headers,
        )
        # Now try to register without token - should fail
        resp = await client.post(
            "/auth/register",
            json={"username": "nouser", "password": "secret123", "rol": "vendedor"},
        )
        assert resp.status_code in (401, 403)

    async def test_register_subsequent_with_admin_succeeds(self, client: AsyncClient, admin_headers):
        """Admin can create new users."""
        resp = await client.post(
            "/auth/register",
            json={"username": "newvendor", "password": "secret123", "rol": "vendedor"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["username"] == "newvendor"
        assert data["rol"] == "vendedor"

    async def test_register_rejects_duplicate_username(self, client: AsyncClient, admin_headers):
        """Register rejects duplicate username."""
        await client.post(
            "/auth/register",
            json={"username": "dupuser", "password": "secret123", "rol": "vendedor"},
            headers=admin_headers,
        )
        resp = await client.post(
            "/auth/register",
            json={"username": "dupuser", "password": "otherpass", "rol": "vendedor"},
            headers=admin_headers,
        )
        assert resp.status_code == 400


class TestAuthLogin:
    """Tests for POST /auth/login."""

    async def test_login_returns_jwt(self, client: AsyncClient, admin_headers):
        """Login returns valid JWT token."""
        # Create user first
        await client.post(
            "/auth/register",
            json={"username": "logintest", "password": "mypass123", "rol": "vendedor"},
            headers=admin_headers,
        )
        resp = await client.post(
            "/auth/login",
            json={"username": "logintest", "password": "mypass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["rol"] == "vendedor"
        assert data["username"] == "logintest"

    async def test_login_rejects_wrong_password(self, client: AsyncClient, admin_headers):
        """Login rejects incorrect password."""
        await client.post(
            "/auth/register",
            json={"username": "badpass", "password": "correctpass", "rol": "vendedor"},
            headers=admin_headers,
        )
        resp = await client.post(
            "/auth/login",
            json={"username": "badpass", "password": "wrongpass"},
        )
        assert resp.status_code == 401

    async def test_login_rejects_inactive_user(self, client: AsyncClient, session, admin_headers):
        """Login rejects inactive user."""
        from app.models import User
        from app.core.security import hash_password

        user = User(username="inactive", hashed_password=hash_password("pass123"), rol="vendedor", activo=False)
        session.add(user)
        session.commit()

        resp = await client.post(
            "/auth/login",
            json={"username": "inactive", "password": "pass123"},
        )
        assert resp.status_code == 401


class TestAuthMe:
    """Tests for GET /auth/me."""

    async def test_me_returns_current_user(self, client: AsyncClient, admin_headers):
        """GET /auth/me returns current user info."""
        resp = await client.get("/auth/me", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["rol"] == "admin"

    async def test_me_rejects_no_token(self, client: AsyncClient):
        """GET /auth/me rejects request without token."""
        resp = await client.get("/auth/me")
        assert resp.status_code == 401


class TestAuthPassword:
    """Tests for POST /auth/password."""

    async def test_change_password_valid(self, client: AsyncClient, admin_headers):
        """Change password with correct current password succeeds."""
        # Register a new user first
        await client.post(
            "/auth/register",
            json={"username": "pwdtest", "password": "oldpass123", "rol": "vendedor"},
            headers=admin_headers,
        )
        # Login as that user
        login_resp = await client.post(
            "/auth/login",
            json={"username": "pwdtest", "password": "oldpass123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Change password
        resp = await client.post(
            "/auth/password",
            json={"current": "oldpass123", "new": "newpass123"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Verify new password works
        login_resp2 = await client.post(
            "/auth/login",
            json={"username": "pwdtest", "password": "newpass123"},
        )
        assert login_resp2.status_code == 200

    async def test_change_password_rejects_wrong_current(self, client: AsyncClient, admin_headers):
        """Change password rejects incorrect current password."""
        await client.post(
            "/auth/register",
            json={"username": "pwdtest2", "password": "oldpass123", "rol": "vendedor"},
            headers=admin_headers,
        )
        login_resp = await client.post(
            "/auth/login",
            json={"username": "pwdtest2", "password": "oldpass123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/auth/password",
            json={"current": "wrongpass", "new": "newpass123"},
            headers=headers,
        )
        assert resp.status_code == 401


class TestAuthUsers:
    """Tests for GET /auth/users."""

    async def test_list_users_admin(self, client: AsyncClient, admin_headers):
        """Admin can list all users."""
        resp = await client.get("/auth/users", headers=admin_headers)
        assert resp.status_code == 200
        users = resp.json()
        assert isinstance(users, list)
        assert len(users) >= 1  # at least admin
        for u in users:
            assert "id" in u
            assert "username" in u
            assert "rol" in u
            assert "activo" in u

    async def test_list_users_rejects_vendedor(self, client: AsyncClient, vendedor_headers):
        """Vendedor cannot list users."""
        resp = await client.get("/auth/users", headers=vendedor_headers)
        assert resp.status_code == 403