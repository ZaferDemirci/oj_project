from fastapi import APIRouter, Request, HTTPException, status
from app.models.user import User, UserCreate, UserResponse
from app.repositories.user_repository import UserRepository
from app.utils.password import hash_password, verify_password
from datetime import datetime

router = APIRouter()
user_repo = UserRepository()

# Endpoints

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    # Check if user exists
    existing = user_repo.get_by_username(user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )
    
    # Create new user (default student)
    new_user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        role="student",
        is_active=True
    )
    
    try:
        user_repo.create(new_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    
    return {"code": 201, "message": "User registered successfully", "data": None}

@router.post("/login")
async def login(request: Request, user_data: UserCreate):
    # Find user
    user = user_repo.get_by_username(user_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check if active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Verify password
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Set session
    request.session["user_id"] = user.id
    
    return {
        "code": 200,
        "message": "Login successful",
        "data": UserResponse.from_user(user).model_dump()
    }

@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"code": 200, "message": "Logged out successfully", "data": None}

@router.get("/me")
async def get_current_user(request: Request):
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
    
    return {
        "code": 200,
        "message": "ok",
        "data": UserResponse.from_user(user).model_dump()
    }