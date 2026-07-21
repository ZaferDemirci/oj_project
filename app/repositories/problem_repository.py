import json
import os
from typing import List, Optional
from app.models.problem import Problem
from app.repositories.base import BaseRepository

DATA_DIR = "data"
PROBLEMS_FILE = f"{DATA_DIR}/problems.json"

class ProblemRepository(BaseRepository):
    def __init__(self):
        super().__init__(PROBLEMS_FILE) # Initialize base with the file path, if file doesn't exist, initialize it with an empty dict
        if self._load_data() is None:
            self._save_data({})

    # Override _load_data to return dict
    def _load_data(self) -> dict:
        data = super()._load_data()
        if data is None:
            return {}
        return data

    def get_all(self) -> List[Problem]:
        data = self._load_data()
        return [Problem(**item) for item in data.values()]

    def get_by_id(self, problem_id: str) -> Optional[Problem]:
        data = self._load_data()
        if problem_id in data:
            return Problem(**data[problem_id])
        return None

    def create(self, problem: Problem) -> Problem:
        data = self._load_data()
        if problem.id in data:
            raise ValueError(f"Problem with id '{problem.id}' already exists")
        data[problem.id] = problem.model_dump()
        self._save_data(data)
        return problem

    def update(self, problem: Problem) -> Problem:
        data = self._load_data()
        if problem.id not in data:
            raise ValueError(f"Problem with id '{problem.id}' not found")
        data[problem.id] = problem.model_dump()
        self._save_data(data)
        return problem

    def delete(self, problem_id: str) -> bool:
        data = self._load_data()
        if problem_id not in data:
            return False
        del data[problem_id]
        self._save_data(data)
        return True

    def exists(self, problem_id: str) -> bool:
        data = self._load_data()
        return problem_id in data