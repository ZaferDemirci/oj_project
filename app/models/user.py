from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid
from typing import Optional

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    password_hash: str  # NEVER return this in API responses
    role: str = "student"  # student, teacher, admin
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("username")
    def validate_username(cls, v):
        if not 3 <= len(v) <= 32:
            raise ValueError("Username must be between 3 and 32 characters")
        return v

class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator("username")
    def validate_username(cls, v):
        if not 3 <= len(v) <= 32:
            raise ValueError("Username must be between 3 and 32 characters")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Convert from User model, excluding password_hash
    @classmethod
    def from_user(cls, user: User):
        return cls(
            id=user.id,
            username=user.username,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

class UserUpdate(BaseModel):
    role: Optional[str] = Field(None, pattern=r"^(student|teacher|admin)$")
    is_active: Optional[bool] = None