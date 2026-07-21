from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid

class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operator_id: str
    action: str  # e.g., "VIEW_FULL_JUDGE_LOG", "REJUDGE_SUBMISSION", "UPDATE_USER_ROLE", "DISABLE_USER", "CREATE_BACKUP", "RESTORE_BACKUP"
    target_type: Optional[str] = None  # "submission", "user", "problem", "backup"
    target_id: Optional[str] = None
    success: bool = True
    detail: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def create_log(cls, operator_id: str, action: str, **kwargs):
        return cls(
            operator_id=operator_id,
            action=action,
            target_type=kwargs.get("target_type"),
            target_id=kwargs.get("target_id"),
            success=kwargs.get("success", True),
            detail=kwargs.get("detail"),
        )