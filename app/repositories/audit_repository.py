import json
import os
from typing import List, Optional
from app.models.audit import AuditLog
from app.repositories.base import BaseRepository

DATA_DIR = "data"
AUDIT_FILE = f"{DATA_DIR}/audit_logs.json"

class AuditRepository(BaseRepository):
    def __init__(self):
        super().__init__(AUDIT_FILE)
        if self._load_data() is None:
            self._save_data([])

    def _load_data(self) -> List[dict]:
        data = super()._load_data()
        if data is None:
            return []
        return data

    def create(self, log: AuditLog) -> AuditLog:
        data = self._load_data()
        data.append(log.model_dump())
        self._save_data(data)
        return log

    def get_all(self, filters: dict = None) -> List[AuditLog]:
        data = self._load_data()
        logs = [AuditLog(**item) for item in data]
        if filters:
            if filters.get("operator_id"):
                logs = [l for l in logs if l.operator_id == filters["operator_id"]]
            if filters.get("action"):
                logs = [l for l in logs if l.action == filters["action"]]
            if filters.get("target_id"):
                logs = [l for l in logs if l.target_id == filters["target_id"]]
            if filters.get("start_time"):
                logs = [l for l in logs if l.created_at >= filters["start_time"]]
            if filters.get("end_time"):
                logs = [l for l in logs if l.created_at <= filters["end_time"]]
        logs.sort(key=lambda l: l.created_at, reverse=True)
        return logs