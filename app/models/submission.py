from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Literal
import uuid

# Enums

SubmissionStatus = Literal["pending", "running", "finished", "failed"]
JudgeResult = Literal["AC", "WA", "RE", "TLE", "SE"]

# Main Submission Model

class Submission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    problem_id: str
    language: str = "python"  # only python is supported
    source_code: str
    status: SubmissionStatus = "pending"
    result: Optional[JudgeResult] = None
    score: int = 0
    total_time: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    judge_result: Optional[dict] = None # full judge result as dict so I can serialize it to JSON later

    @field_validator("source_code")
    def validate_source_code(cls, v):
        if not v or not v.strip():
            raise ValueError("Source code cannot be empty")
        if len(v) > 64 * 1024:  # 64 KiB limit
            raise ValueError("Source code exceeds 64 KiB limit")
        return v

    @field_validator("language")
    def validate_language(cls, v):
        if v != "python":
            raise ValueError("Only 'python' language is supported")
        return v


# Request/Response Models

class SubmissionCreate(BaseModel):
    problem_id: str
    language: str = "python"
    source_code: str

    @field_validator("source_code")
    def validate_source_code(cls, v):
        if not v or not v.strip():
            raise ValueError("Source code cannot be empty")
        if len(v) > 64 * 1024:
            raise ValueError("Source code exceeds 64 KiB limit")
        return v

    @field_validator("language")
    def validate_language(cls, v):
        if v != "python":
            raise ValueError("Only 'python' language is supported")
        return v


class SubmissionResponse(BaseModel):
    id: str
    user_id: str
    problem_id: str
    language: str
    status: SubmissionStatus
    result: Optional[JudgeResult]
    score: int
    total_time: Optional[float]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    @classmethod
    def from_submission(cls, sub: Submission):
        return cls(
            id=sub.id,
            user_id=sub.user_id,
            problem_id=sub.problem_id,
            language=sub.language,
            status=sub.status,
            result=sub.result,
            score=sub.score,
            total_time=sub.total_time,
            created_at=sub.created_at,
            started_at=sub.started_at,
            finished_at=sub.finished_at,
        )


# Filter parameters for GET /api/submissions

class SubmissionFilters(BaseModel):
    problem_id: Optional[str] = None
    user_id: Optional[str] = None
    status: Optional[SubmissionStatus] = None
    result: Optional[JudgeResult] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)