import json
import os
from typing import List, Optional
from app.models.user import User
from app.repositories.base import BaseRepository

DATA_DIR = "data"
USERS_FILE = f"{DATA_DIR}/users.json"

class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(USERS_FILE)
        if self._load_data() is None:
            self._save_data([])

    def _load_data(self) -> List[dict]:
        data = super()._load_data()
        if data is None:
            return []
        return data  # Expecting a list of dicts

    def get_all(self) -> List[User]:
        return [User(**item) for item in self._load_data()]

    def get_by_id(self, user_id: str) -> Optional[User]:
        for item in self._load_data():
            if item["id"] == user_id:
                return User(**item)
        return None

    def get_by_username(self, username: str) -> Optional[User]:
        for item in self._load_data():
            if item["username"].lower() == username.lower():
                return User(**item)
        return None

    def create(self, user: User) -> User:
        data = self._load_data()
        if any(u["username"].lower() == user.username.lower() for u in data):
            raise ValueError("Username already exists")
        data.append(user.model_dump())
        self._save_data(data)
        return user

    def update(self, user: User) -> User:
        data = self._load_data()
        for idx, item in enumerate(data):
            if item["id"] == user.id:
                data[idx] = user.model_dump()
                self._save_data(data)
                return user
        raise ValueError("User not found")