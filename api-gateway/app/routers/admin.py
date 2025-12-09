"""
Admin router.

Administrative endpoints for user management.
Requires ADMIN role for all operations.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import MessageResponse, UserResponse
from app.services.auth import (
    approve_user,
    delete_user,
    get_user_by_id,
    list_all_users,
    list_pending_users,
    make_user_admin,
    revoke_user_admin,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    List all users in the system.

    **Requires:** ADMIN role

    **Returns:** List of users ordered by registration date

    **Errors:**
    - 401: Not authenticated
    - 403: Not an admin
    """
    users = await list_all_users(db)
    return [UserResponse.model_validate(user) for user in users]


@router.get("/pending-users", response_model=list[UserResponse])
async def get_pending_users(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """
    List all users with PENDING status awaiting approval.

    **Requires:** ADMIN role

    **Returns:** List of pending users ordered by registration date

    **Errors:**
    - 401: Not authenticated
    - 403: Not an admin
    """
    users = await list_pending_users(db)
    return [UserResponse.model_validate(user) for user in users]


@router.post("/approve/{user_id}", response_model=UserResponse)
async def approve_user_endpoint(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Approve a pending user (change status to ACTIVE).

    **Requires:** ADMIN role

    **Flow:**
    1. Admin views pending users via `/admin/pending-users`
    2. Admin approves a user by their UUID
    3. User status changes from PENDING → ACTIVE
    4. User can now log in and access the system

    **Errors:**
    - 400: User not found, already approved, or disabled
    - 401: Not authenticated
    - 403: Not an admin
    """
    try:
        user = await approve_user(db, user_id)
        logger.info(f"Admin {admin.email} action: approve user {user_id} ({user.email})")
        return UserResponse.model_validate(user)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/make-admin/{user_id}", response_model=UserResponse)
async def make_admin_endpoint(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Grant ADMIN role to a user.

    **Requires:** ADMIN role

    **Flow:**
    1. Admin views all users via `/admin/users`
    2. Admin selects a user and calls this endpoint
    3. User role changes from USER → ADMIN

    **Errors:**
    - 400: User not found or already admin
    - 401: Not authenticated
    - 403: Not an admin
    """
    try:
        user = await make_user_admin(db, user_id)
        logger.info(f"Admin {admin.email} action: make-admin user {user_id} ({user.email})")
        return UserResponse.model_validate(user)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post("/revoke-admin/{user_id}", response_model=UserResponse)
async def revoke_admin_endpoint(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Revoke ADMIN role from a user (change to USER).

    **Requires:** ADMIN role

    **Flow:**
    1. Admin views all users via `/admin/users`
    2. Admin selects an admin user and calls this endpoint
    3. User role changes from ADMIN → USER

    **Notes:**
    - Admin cannot revoke their own admin rights to prevent accidental lockout

    **Errors:**
    - 400: User not found, not an admin, or trying to revoke self
    - 401: Not authenticated
    - 403: Not an admin
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot revoke your own administrator privileges.",
        )

    try:
        user = await revoke_user_admin(db, user_id)
        logger.info(f"Admin {admin.email} action: revoke-admin user {user_id} ({user.email})")
        return UserResponse.model_validate(user)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user_endpoint(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Permanently delete a user from the system.

    **Requires:** ADMIN role

    **Notes:**
    - Admin cannot delete their own account to prevent accidental lockout

    **Errors:**
    - 400: User not found or trying to delete self
    - 401: Not authenticated
    - 403: Not an admin
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own administrator account.",
        )

    try:
        user = await get_user_by_id(db, user_id)
        user_email = user.email if user else "unknown"
        await delete_user(db, user_id)
        logger.info(f"Admin {admin.email} action: delete user {user_id} ({user_email})")
        return MessageResponse(message="User deleted successfully")

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
