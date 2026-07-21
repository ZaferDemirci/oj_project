import json
import os
from typing import List, Optional
from datetime import datetime
from app.models.submission import Submission, SubmissionFilters
from app.repositories.base import BaseRepository

DATA_DIR = "data"
SUBMISSIONS_FILE = f"{DATA_DIR}/submissions.json"

class SubmissionRepository(BaseRepository):
    def __init__(self):
        super().__init__(SUBMISSIONS_FILE)
        if self._load_data() is None:
            self._save_data({})

    def _load_data(self) -> dict:
        data = super()._load_data()
        if data is None:
            return {}
        return data

    def get_all(self, filters: Optional[SubmissionFilters] = None) -> List[Submission]:
        data = self._load_data()
        submissions = [Submission(**item) for item in data.values()]

        if filters:
            if filters.problem_id:
                submissions = [s for s in submissions if s.problem_id == filters.problem_id]
            if filters.user_id:
                submissions = [s for s in submissions if s.user_id == filters.user_id]
            if filters.status:
                submissions = [s for s in submissions if s.status == filters.status]
            if filters.result:
                submissions = [s for s in submissions if s.result == filters.result]
            if filters.start_time:
                submissions = [s for s in submissions if s.created_at >= filters.start_time]
            if filters.end_time:
                submissions = [s for s in submissions if s.created_at <= filters.end_time]

        submissions.sort(key=lambda s: s.created_at, reverse=True)
        return submissions

    def get_by_id(self, submission_id: str) -> Optional[Submission]:
        data = self._load_data()
        if submission_id in data:
            return Submission(**data[submission_id])
        return None

    def create(self, submission: Submission) -> Submission:
        data = self._load_data()
        data[submission.id] = submission.model_dump()
        self._save_data(data)
        return submission

    def update(self, submission: Submission) -> Submission:
        data = self._load_data()
        if submission.id not in data:
            raise ValueError(f"Submission with id '{submission.id}' not found")
        data[submission.id] = submission.model_dump()
        self._save_data(data)
        return submission

    def get_by_problem_id(self, problem_id: str) -> List[Submission]:
        data = self._load_data()
        return [Submission(**item) for item in data.values() if item["problem_id"] == problem_id]