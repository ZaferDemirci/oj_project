import json
import os
from typing import Optional
from datetime import datetime
from app.repositories.base import BaseRepository

DATA_DIR = "data"
SIMILARITY_FILE = f"{DATA_DIR}/similarity_reports.json"

class SimilarityRepository(BaseRepository):
    def __init__(self):
        super().__init__(SIMILARITY_FILE)
        if self._load_data() is None:
            self._save_data({})

    def _load_data(self) -> dict:
        data = super()._load_data()
        if data is None:
            return {}
        return data

    def get_report(self, problem_id: str) -> Optional[dict]:
        data = self._load_data()
        return data.get(problem_id)

    def save_report(self, problem_id: str, report: dict):
        data = self._load_data()
        report["created_at"] = datetime.utcnow().isoformat() + "Z"
        data[problem_id] = report
        self._save_data(data)

    def get_all_reports(self) -> dict:
        return self._load_data()