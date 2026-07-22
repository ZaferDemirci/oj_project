from fastapi import Request, HTTPException, status
from app.repositories.user_repository import UserRepository

user_repo = UserRepository()

async def get_current_user(request: Request):
    """Get the current logged-in user. Raises 401 if not authenticated."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user = user_repo.get_by_id(user_id)
    if not user:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user

def require_role(allowed_roles: list):
    """Factory that returns a dependency requiring a specific role."""
    async def role_dependency(request: Request):
        user = await get_current_user(request)
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(allowed_roles)}"
            )
        return user
    return role_dependency

# Preconfigured dependencies for convenience
require_teacher = require_role(["teacher", "admin"])
require_admin = require_role(["admin"])