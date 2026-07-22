from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.models.user import User, UserResponse, UserUpdate
from app.repositories.user_repository import UserRepository
from app.utils.dependencies import require_admin

router = APIRouter()
user_repo = UserRepository()


@router.get("/users")
async def list_users(
    current_user: User = Depends(require_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all users (admin only). Paginated."""
    all_users = user_repo.get_all()
    total = len(all_users)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = all_users[start:end]

    items = [UserResponse.from_user(u).model_dump() for u in paginated]
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    }


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    current_user: User = Depends(require_admin),
):
    """Get a single user (admin only)."""
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {
        "code": 200,
        "message": "ok",
        "data": UserResponse.from_user(user).model_dump()
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    current_user: User = Depends(require_admin),
):
    """
    Update a user's role or active status (admin only).
    """
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admin from disabling their own account
    if user_id == current_user.id and update_data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account"
        )

    # Apply updates
    if update_data.role is not None:
        user.role = update_data.role
    if update_data.is_active is not None:
        user.is_active = update_data.is_active

    user_repo.update(user)

    return {
        "code": 200,
        "message": "User updated successfully",
        "data": UserResponse.from_user(user).model_dump()
    }