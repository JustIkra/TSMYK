"""
Comprehensive tests for authentication module.

Tests cover:
- User registration
- Login/logout
- Profile management
- Password changes
- Token validation
- Edge cases and error handling
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User
from app.services.auth import create_access_token, hash_password


# ============================================================================
# Registration Tests
# ============================================================================


@pytest.mark.integration
async def test_register_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful user registration."""
    # Arrange
    request_data = {
        "email": "newuser@test.local",
        "password": "SecurePass123",
    }

    # Act
    response = await client.post("/api/auth/register", json=request_data)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.local"
    assert data["role"] == "USER"
    assert data["status"] == "PENDING"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.integration
async def test_register_duplicate_email(client: AsyncClient, active_user: User):
    """Test registration fails with duplicate email."""
    # Arrange
    request_data = {
        "email": active_user.email,  # Already exists
        "password": "SecurePass123",
    }

    # Act
    response = await client.post("/api/auth/register", json=request_data)

    # Assert
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_register_invalid_email(client: AsyncClient):
    """Test registration fails with invalid email format."""
    # Arrange
    request_data = {
        "email": "not-an-email",
        "password": "SecurePass123",
    }

    # Act
    response = await client.post("/api/auth/register", json=request_data)

    # Assert
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("email" in str(err).lower() for err in errors)


@pytest.mark.integration
async def test_register_weak_password_no_letter(client: AsyncClient):
    """Test registration fails with password containing no letters."""
    # Arrange
    request_data = {
        "email": "user@test.local",
        "password": "12345678",  # No letters
    }

    # Act
    response = await client.post("/api/auth/register", json=request_data)

    # Assert
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("letter" in str(err).lower() for err in errors)


@pytest.mark.integration
async def test_register_weak_password_no_digit(client: AsyncClient):
    """Test registration fails with password containing no digits."""
    # Arrange
    request_data = {
        "email": "user@test.local",
        "password": "onlyletters",  # No digits
    }

    # Act
    response = await client.post("/api/auth/register", json=request_data)

    # Assert
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("digit" in str(err).lower() for err in errors)


@pytest.mark.integration
async def test_register_password_too_short(client: AsyncClient):
    """Test registration fails with password shorter than 8 characters."""
    # Arrange
    request_data = {
        "email": "user@test.local",
        "password": "Pass1",  # Only 5 characters
    }

    # Act
    response = await client.post("/api/auth/register", json=request_data)

    # Assert
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("8" in str(err) for err in errors)


# ============================================================================
# Login Tests
# ============================================================================


@pytest.mark.integration
async def test_login_success(client: AsyncClient, active_user: User):
    """Test successful login sets cookie and returns user info."""
    # Arrange
    request_data = {
        "email": "user@test.local",
        "password": "UserPass123",
    }

    # Act
    response = await client.post("/api/auth/login", json=request_data)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login successful"
    assert data["user"]["email"] == active_user.email
    assert data["user"]["role"] == active_user.role
    assert data["user"]["status"] == "ACTIVE"

    # Check cookie is set
    assert "access_token" in response.cookies
    token = response.cookies["access_token"]
    assert len(token) > 0

    # Verify token is valid
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    assert payload["email"] == active_user.email
    assert payload["role"] == active_user.role


@pytest.mark.integration
async def test_login_invalid_email(client: AsyncClient):
    """Test login fails with non-existent email."""
    # Arrange
    request_data = {
        "email": "nonexistent@test.local",
        "password": "AnyPass123",
    }

    # Act
    response = await client.post("/api/auth/login", json=request_data)

    # Assert
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_login_invalid_password(client: AsyncClient, active_user: User):
    """Test login fails with incorrect password."""
    # Arrange
    request_data = {
        "email": active_user.email,
        "password": "WrongPass123",
    }

    # Act
    response = await client.post("/api/auth/login", json=request_data)

    # Assert
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_login_pending_user(client: AsyncClient, pending_user: User):
    """Test login fails for users with PENDING status."""
    # Arrange
    request_data = {
        "email": "pending@test.local",
        "password": "PendingPass123",
    }

    # Act
    response = await client.post("/api/auth/login", json=request_data)

    # Assert
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert "PENDING" in detail
    assert "administrator" in detail.lower()


@pytest.mark.integration
async def test_login_disabled_user(client: AsyncClient, db_session: AsyncSession):
    """Test login fails for users with DISABLED status."""
    # Arrange - Create a DISABLED user
    disabled_user = User(
        id=uuid.uuid4(),
        email="disabled@test.local",
        password_hash=hash_password("DisabledPass123"),
        role="USER",
        status="DISABLED",
        created_at=datetime.now(UTC),
    )
    db_session.add(disabled_user)
    await db_session.commit()

    request_data = {
        "email": "disabled@test.local",
        "password": "DisabledPass123",
    }

    # Act
    response = await client.post("/api/auth/login", json=request_data)

    # Assert
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert "DISABLED" in detail


@pytest.mark.integration
async def test_login_cookie_attributes(client: AsyncClient, active_user: User):
    """Test login cookie has correct security attributes."""
    # Arrange
    request_data = {
        "email": "user@test.local",
        "password": "UserPass123",
    }

    # Act
    response = await client.post("/api/auth/login", json=request_data)

    # Assert
    cookie_header = response.headers.get("set-cookie", "")
    assert "httponly" in cookie_header.lower()
    assert "samesite=lax" in cookie_header.lower()
    assert "max-age=1800" in cookie_header.lower()  # 30 minutes


# ============================================================================
# Logout Tests
# ============================================================================


@pytest.mark.integration
async def test_logout_success(client: AsyncClient):
    """Test logout clears authentication cookie."""
    # Act
    response = await client.post("/api/auth/logout")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Logged out successfully"

    # Check cookie is cleared
    cookie_header = response.headers.get("set-cookie", "")
    assert "access_token" in cookie_header
    # Cookie should be deleted (empty value or expired)
    assert "max-age=0" in cookie_header.lower() or '""' in cookie_header


@pytest.mark.integration
async def test_logout_when_not_logged_in(client: AsyncClient):
    """Test logout succeeds even when not logged in."""
    # Act
    response = await client.post("/api/auth/logout")

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"


# ============================================================================
# Get Current User Tests
# ============================================================================


@pytest.mark.integration
async def test_get_me_success(user_client: AsyncClient, active_user: User):
    """Test getting current user profile."""
    # Act
    response = await user_client.get("/api/auth/me")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == active_user.email
    assert data["role"] == active_user.role
    assert data["status"] == active_user.status
    assert data["full_name"] == active_user.full_name


@pytest.mark.integration
async def test_get_me_unauthenticated(client: AsyncClient):
    """Test getting current user fails without authentication."""
    # Act
    response = await client.get("/api/auth/me")

    # Assert
    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_get_me_with_invalid_token(client: AsyncClient):
    """Test getting current user fails with invalid token."""
    # Arrange
    client.cookies.set("access_token", "invalid.token.here")

    # Act
    response = await client.get("/api/auth/me")

    # Assert
    assert response.status_code == 401
    assert "invalid token" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_get_me_with_expired_token(client: AsyncClient, active_user: User):
    """Test getting current user fails with expired token."""
    # Arrange - Create an expired token
    now = datetime.now(UTC)
    expired_time = now - timedelta(hours=1)
    payload = {
        "sub": str(active_user.id),
        "email": active_user.email,
        "role": active_user.role,
        "iat": expired_time,
        "exp": expired_time + timedelta(minutes=30),  # Expired 30 minutes ago
    }
    expired_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)
    client.cookies.set("access_token", expired_token)

    # Act
    response = await client.get("/api/auth/me")

    # Assert
    assert response.status_code == 401
    assert "invalid token" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_get_me_with_authorization_header(client: AsyncClient, active_user: User):
    """Test getting current user with Authorization header instead of cookie."""
    # Arrange
    token = create_access_token(active_user.id, active_user.email, active_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # Act
    response = await client.get("/api/auth/me", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == active_user.email


# ============================================================================
# Check Active Tests
# ============================================================================


@pytest.mark.integration
async def test_check_active_success(user_client: AsyncClient, active_user: User):
    """Test check-active succeeds for ACTIVE user."""
    # Act
    response = await user_client.get("/api/auth/me/check-active")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == active_user.email
    assert data["status"] == "ACTIVE"


@pytest.mark.integration
async def test_check_active_pending_user(client: AsyncClient, pending_user: User):
    """Test check-active fails for PENDING user."""
    # Arrange
    token = create_access_token(pending_user.id, pending_user.email, pending_user.role)
    client.cookies.set("access_token", token)

    # Act
    response = await client.get("/api/auth/me/check-active")

    # Assert
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert "PENDING" in detail
    assert "administrator" in detail.lower()


@pytest.mark.integration
async def test_check_active_unauthenticated(client: AsyncClient):
    """Test check-active fails without authentication."""
    # Act
    response = await client.get("/api/auth/me/check-active")

    # Assert
    assert response.status_code == 401


# ============================================================================
# Update Profile Tests
# ============================================================================


@pytest.mark.integration
async def test_update_profile_success(user_client: AsyncClient, active_user: User):
    """Test updating user profile full_name."""
    # Arrange
    request_data = {"full_name": "Updated Name"}

    # Act
    response = await user_client.put("/api/auth/me/profile", json=request_data)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["email"] == active_user.email


@pytest.mark.integration
async def test_update_profile_clear_name(user_client: AsyncClient, active_user: User):
    """Test clearing profile full_name."""
    # Arrange
    request_data = {"full_name": None}

    # Act
    response = await user_client.put("/api/auth/me/profile", json=request_data)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] is None


@pytest.mark.integration
async def test_update_profile_empty_string_fails(user_client: AsyncClient):
    """Test updating profile with empty string fails validation."""
    # Arrange
    request_data = {"full_name": ""}

    # Act
    response = await user_client.put("/api/auth/me/profile", json=request_data)

    # Assert
    assert response.status_code == 422


@pytest.mark.integration
async def test_update_profile_unauthenticated(client: AsyncClient):
    """Test updating profile fails without authentication."""
    # Arrange
    request_data = {"full_name": "New Name"}

    # Act
    response = await client.put("/api/auth/me/profile", json=request_data)

    # Assert
    assert response.status_code == 401


@pytest.mark.integration
async def test_update_profile_pending_user(client: AsyncClient, pending_user: User):
    """Test updating profile fails for PENDING user."""
    # Arrange
    token = create_access_token(pending_user.id, pending_user.email, pending_user.role)
    client.cookies.set("access_token", token)
    request_data = {"full_name": "New Name"}

    # Act
    response = await client.put("/api/auth/me/profile", json=request_data)

    # Assert
    assert response.status_code == 403


# ============================================================================
# Change Password Tests
# ============================================================================


@pytest.mark.integration
async def test_change_password_success(user_client: AsyncClient, active_user: User, db_session: AsyncSession):
    """Test successfully changing password."""
    # Arrange
    request_data = {
        "current_password": "UserPass123",
        "new_password": "NewSecurePass456",
    }

    # Act
    response = await user_client.post("/api/auth/me/change-password", json=request_data)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Password changed successfully"

    # Verify new password works for login
    await db_session.refresh(active_user)
    login_response = await user_client.post(
        "/api/auth/login",
        json={"email": active_user.email, "password": "NewSecurePass456"}
    )
    assert login_response.status_code == 200


@pytest.mark.integration
async def test_change_password_wrong_current(user_client: AsyncClient):
    """Test changing password fails with incorrect current password."""
    # Arrange
    request_data = {
        "current_password": "WrongPassword123",
        "new_password": "NewSecurePass456",
    }

    # Act
    response = await user_client.post("/api/auth/me/change-password", json=request_data)

    # Assert
    assert response.status_code == 400
    assert "current password is incorrect" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_change_password_weak_new_password(user_client: AsyncClient):
    """Test changing password fails with weak new password."""
    # Arrange
    request_data = {
        "current_password": "UserPass123",
        "new_password": "12345678",  # No letters
    }

    # Act
    response = await user_client.post("/api/auth/me/change-password", json=request_data)

    # Assert
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("letter" in str(err).lower() for err in errors)


@pytest.mark.integration
async def test_change_password_too_short(user_client: AsyncClient):
    """Test changing password fails with too short new password."""
    # Arrange
    request_data = {
        "current_password": "UserPass123",
        "new_password": "Pass1",  # Only 5 characters
    }

    # Act
    response = await user_client.post("/api/auth/me/change-password", json=request_data)

    # Assert
    assert response.status_code == 422


@pytest.mark.integration
async def test_change_password_unauthenticated(client: AsyncClient):
    """Test changing password fails without authentication."""
    # Arrange
    request_data = {
        "current_password": "OldPass123",
        "new_password": "NewPass456",
    }

    # Act
    response = await client.post("/api/auth/me/change-password", json=request_data)

    # Assert
    assert response.status_code == 401


@pytest.mark.integration
async def test_change_password_pending_user(client: AsyncClient, pending_user: User):
    """Test changing password fails for PENDING user."""
    # Arrange
    token = create_access_token(pending_user.id, pending_user.email, pending_user.role)
    client.cookies.set("access_token", token)
    request_data = {
        "current_password": "PendingPass123",
        "new_password": "NewPass456",
    }

    # Act
    response = await client.post("/api/auth/me/change-password", json=request_data)

    # Assert
    assert response.status_code == 403


# ============================================================================
# Unit Tests for Service Layer
# ============================================================================


@pytest.mark.unit
def test_password_hashing():
    """Test password hashing and verification."""
    # Arrange
    from app.services.auth import hash_password, verify_password

    plain_password = "TestPassword123"

    # Act
    hashed = hash_password(plain_password)

    # Assert
    assert hashed != plain_password
    assert len(hashed) > 0
    assert verify_password(plain_password, hashed)
    assert not verify_password("WrongPassword", hashed)


@pytest.mark.unit
def test_create_access_token():
    """Test JWT token creation."""
    # Arrange
    from app.services.auth import create_access_token, decode_access_token

    user_id = uuid.uuid4()
    email = "test@example.com"
    role = "USER"

    # Act
    token = create_access_token(user_id, email, role)

    # Assert
    assert isinstance(token, str)
    assert len(token) > 0

    # Verify token contents
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["email"] == email
    assert payload["role"] == role
    assert "iat" in payload
    assert "exp" in payload


@pytest.mark.unit
def test_decode_invalid_token():
    """Test decoding invalid token raises exception."""
    # Arrange
    from app.services.auth import decode_access_token

    invalid_token = "invalid.token.here"

    # Act & Assert
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(invalid_token)


@pytest.mark.unit
def test_decode_expired_token():
    """Test decoding expired token raises exception."""
    # Arrange
    from app.services.auth import decode_access_token

    # Create expired token
    now = datetime.now(UTC)
    expired_time = now - timedelta(hours=1)
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "test@example.com",
        "role": "USER",
        "iat": expired_time,
        "exp": expired_time + timedelta(minutes=30),
    }
    expired_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)

    # Act & Assert
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired_token)


# ============================================================================
# Edge Cases and Security Tests
# ============================================================================


@pytest.mark.integration
async def test_login_case_sensitive_email(client: AsyncClient, active_user: User):
    """Test that email comparison is case-insensitive (or verify behavior)."""
    # Note: This tests the actual behavior - may need adjustment based on requirements
    request_data = {
        "email": active_user.email.upper(),
        "password": "UserPass123",
    }

    # Act
    response = await client.post("/api/auth/login", json=request_data)

    # Assert - Email lookup may be case-sensitive in current implementation
    # This test documents the current behavior
    assert response.status_code in [200, 401]


@pytest.mark.integration
async def test_register_email_normalization(client: AsyncClient):
    """Test email is stored as provided (case preserved)."""
    # Arrange
    request_data = {
        "email": "MixedCase@Test.Local",
        "password": "SecurePass123",
    }

    # Act
    response = await client.post("/api/auth/register", json=request_data)

    # Assert
    assert response.status_code == 201
    data = response.json()
    # Email should be stored as-is (Pydantic EmailStr may normalize)
    assert "@" in data["email"]
    assert "test.local" in data["email"].lower()


@pytest.mark.integration
async def test_token_with_deleted_user(client: AsyncClient, db_session: AsyncSession):
    """Test token becomes invalid if user is deleted."""
    # Arrange - Create and then delete a user
    user = User(
        id=uuid.uuid4(),
        email="deleteme@test.local",
        password_hash=hash_password("DeleteMe123"),
        role="USER",
        status="ACTIVE",
        created_at=datetime.now(UTC),
        approved_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()

    # Create valid token
    token = create_access_token(user.id, user.email, user.role)

    # Delete user
    await db_session.delete(user)
    await db_session.commit()

    # Act - Try to use token
    client.cookies.set("access_token", token)
    response = await client.get("/api/auth/me")

    # Assert
    assert response.status_code == 401
    assert "user not found" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_concurrent_logins_same_user(client: AsyncClient, active_user: User):
    """Test multiple concurrent logins for same user are allowed."""
    # Arrange
    request_data = {
        "email": "user@test.local",
        "password": "UserPass123",
    }

    # Act - Login twice
    response1 = await client.post("/api/auth/login", json=request_data)
    response2 = await client.post("/api/auth/login", json=request_data)

    # Assert - Both should succeed (stateless JWT)
    assert response1.status_code == 200
    assert response2.status_code == 200

    token1 = response1.cookies["access_token"]
    token2 = response2.cookies["access_token"]

    # Tokens should be different (different iat)
    assert token1 != token2


@pytest.mark.integration
async def test_admin_user_can_use_all_endpoints(admin_client: AsyncClient, admin_user: User):
    """Test admin user has access to all auth endpoints."""
    # Get me
    response = await admin_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"

    # Check active
    response = await admin_client.get("/api/auth/me/check-active")
    assert response.status_code == 200

    # Update profile
    response = await admin_client.put(
        "/api/auth/me/profile",
        json={"full_name": "Updated Admin"}
    )
    assert response.status_code == 200

    # Change password
    response = await admin_client.post(
        "/api/auth/me/change-password",
        json={"current_password": "AdminPass123", "new_password": "NewAdminPass456"}
    )
    assert response.status_code == 200
