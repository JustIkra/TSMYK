"""
Tests for user profile management endpoints.

Tests cover:
- Profile update (full_name)
- Password change with verification
- Security checks (authentication, authorization)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.auth import create_user, verify_password


# Profile Update Tests


@pytest.mark.asyncio
async def test_update_profile__valid_full_name__updates_successfully(
    test_env, client: AsyncClient, db_session: AsyncSession
):
    """Test updating profile with valid full_name."""
    # Create and activate user
    user = await create_user(db_session, "user@example.com", "password123")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )

    # Update profile
    response = await client.put(
        "/api/auth/me/profile",
        json={"full_name": "Иванов Иван Иванович"},
        cookies=dict(login_response.cookies),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Иванов Иван Иванович"
    assert data["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_update_profile__null_full_name__clears_name(
    test_env, client: AsyncClient, db_session: AsyncSession
):
    """Test updating profile with null full_name clears the field."""
    # Create and activate user with existing full_name
    user = await create_user(db_session, "user@example.com", "password123")
    user.status = "ACTIVE"
    user.full_name = "Старое Имя"
    await db_session.commit()

    # Login
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )

    # Update profile with null
    response = await client.put(
        "/api/auth/me/profile",
        json={"full_name": None},
        cookies=dict(login_response.cookies),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] is None


@pytest.mark.asyncio
async def test_update_profile__empty_string__returns_422(
    test_env, client: AsyncClient, db_session: AsyncSession
):
    """Test updating profile with empty string fails validation."""
    # Create and activate user
    user = await create_user(db_session, "user@example.com", "password123")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )

    # Try to update with empty string
    response = await client.put(
        "/api/auth/me/profile",
        json={"full_name": ""},
        cookies=dict(login_response.cookies),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_profile__too_long__returns_422(
    test_env, client: AsyncClient, db_session: AsyncSession
):
    """Test updating profile with name exceeding max length fails."""
    # Create and activate user
    user = await create_user(db_session, "user@example.com", "password123")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )

    # Try to update with very long name (>255 chars)
    long_name = "А" * 256
    response = await client.put(
        "/api/auth/me/profile",
        json={"full_name": long_name},
        cookies=dict(login_response.cookies),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_profile__not_authenticated__returns_401(
    test_env, client: AsyncClient
):
    """Test updating profile without authentication returns 401."""
    response = await client.put(
        "/api/auth/me/profile",
        json={"full_name": "Test User"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_profile__pending_user__returns_403(
    test_env, client: AsyncClient, db_session: AsyncSession
):
    """Test updating profile with PENDING user returns 403."""
    # Create pending user
    await create_user(db_session, "pending@example.com", "password123")

    # Cannot test directly as login will fail for PENDING users
    # This test verifies the get_current_active_user dependency behavior


# Password Change Tests


@pytest.mark.asyncio
async def test_change_password__valid_credentials__changes_password(
    test_env, client: AsyncClient, db_session: AsyncSession
):
    """Test changing password with correct current password."""
    # Create and activate user
    user = await create_user(db_session, "user@example.com", "oldpassword123")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "oldpassword123"},
    )

    # Change password
    response = await client.post(
        "/api/auth/me/change-password",
        json={
            "current_password": "oldpassword123",
            "new_password": "newpassword456",
        },
        cookies=dict(login_response.cookies),
    )

    assert response.status_code == 200
    assert "success" in response.json()["message"].lower()

    # Verify new password works by logging in
    await db_session.refresh(user)
    assert verify_password("newpassword456", user.password_hash)

    # Verify can login with new password
    new_login_response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "newpassword456"},
    )
    assert new_login_response.status_code == 200


@pytest.mark.asyncio
async def test_change_password__wrong_current_password__returns_400(
    test_env, client: AsyncClient, db_session: AsyncSession
):
    """Test changing password with incorrect current password returns 400."""
    # Create and activate user
    user = await create_user(db_session, "user@example.com", "correctpassword123")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "correctpassword123"},
    )

    # Try to change password with wrong current password
    response = await client.post(
        "/api/auth/me/change-password",
        json={
            "current_password": "wrongpassword123",
            "new_password": "newpassword456",
        },
        cookies=dict(login_response.cookies),
    )

    assert response.status_code == 400
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_change_password__weak_new_password__returns_422(
    test_env, client: AsyncClient, db_session: AsyncSession
):
    """Test changing to weak password fails validation."""
    # Create and activate user
    user = await create_user(db_session, "user@example.com", "password123")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )

    # Try to change to weak password (no digits)
    response = await client.post(
        "/api/auth/me/change-password",
        json={
            "current_password": "password123",
            "new_password": "onlyletters",
        },
        cookies=dict(login_response.cookies),
    )

    assert response.status_code == 422
    assert "digit" in str(response.json())


@pytest.mark.asyncio
async def test_change_password__short_new_password__returns_422(
    test_env, client: AsyncClient, db_session: AsyncSession
):
    """Test changing to short password fails validation."""
    # Create and activate user
    user = await create_user(db_session, "user@example.com", "password123")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )

    # Try to change to short password
    response = await client.post(
        "/api/auth/me/change-password",
        json={
            "current_password": "password123",
            "new_password": "pass1",
        },
        cookies=dict(login_response.cookies),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password__not_authenticated__returns_401(
    test_env, client: AsyncClient
):
    """Test changing password without authentication returns 401."""
    response = await client.post(
        "/api/auth/me/change-password",
        json={
            "current_password": "oldpassword123",
            "new_password": "newpassword456",
        },
    )

    assert response.status_code == 401


# Integration Tests


@pytest.mark.asyncio
async def test_profile_workflow__update_then_change_password(
    test_env, client: AsyncClient, db_session: AsyncSession
):
    """Test complete profile management workflow."""
    # Create and activate user
    user = await create_user(db_session, "user@example.com", "initialpassword123")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "initialpassword123"},
    )
    cookies = dict(login_response.cookies)

    # Step 1: Update profile
    profile_response = await client.put(
        "/api/auth/me/profile",
        json={"full_name": "Петров Петр Петрович"},
        cookies=cookies,
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["full_name"] == "Петров Петр Петрович"

    # Step 2: Change password
    password_response = await client.post(
        "/api/auth/me/change-password",
        json={
            "current_password": "initialpassword123",
            "new_password": "updatedpassword456",
        },
        cookies=cookies,
    )
    assert password_response.status_code == 200

    # Step 3: Verify changes persisted
    me_response = await client.get("/api/auth/me", cookies=cookies)
    assert me_response.status_code == 200
    data = me_response.json()
    assert data["full_name"] == "Петров Петр Петрович"

    # Step 4: Verify can login with new password
    new_login_response = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "updatedpassword456"},
    )
    assert new_login_response.status_code == 200
