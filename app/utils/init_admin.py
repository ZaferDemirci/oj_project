import os
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.utils.password import hash_password


def ensure_admin_exists():
    repo = UserRepository()
    admin_username = os.getenv("ADMIN_USERNAME", "admin") # DEVELOPMENT DEFAULTS, MUST CHANGE IN PROD
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123") # DEVELOPMENT DEFAULTS, MUST CHANGE IN PROD
    
    existing = repo.get_by_username(admin_username)
    if existing:
        print(f"Admin user '{admin_username}' already exists.")
        return
    
    admin = User(
        username=admin_username,
        password_hash=hash_password(admin_password),
        role="admin",
        is_active=True
    )
    repo.create(admin)
    print(f"Admin user '{admin_username}' created with default password.")