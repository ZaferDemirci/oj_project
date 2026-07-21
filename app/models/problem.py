from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
import re

# Submodels

class Sample(BaseModel):
    input: str
    output: str

class TestCase(BaseModel):
    case_id: str
    input: str
    output: str
    score: int = Field(ge=0, description="Score for this test case")
    is_hidden: bool = False

    @field_validator("case_id")
    def validate_case_id(cls, v):
        if not v or len(v) > 64:
            raise ValueError("case_id must be 1-64 characters")
        return v

# Main Problem Model

class Problem(BaseModel):
    id: str = Field(..., min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(..., min_length=1, max_length=100)
    description: str
    input_description: str
    output_description: str
    samples: List[Sample] = Field(..., min_length=1)
    constraints: Optional[str] = None
    time_limit: float = Field(gt=0, description="Time limit in seconds")
    memory_limit: int = Field(gt=0, description="Memory limit in MB")
    difficulty: str = Field(..., pattern=r"^(easy|medium|hard)$")
    tags: List[str] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_test_case_scores(self) -> "Problem":
        total = sum(tc.score for tc in self.test_cases)
        if total != 100:
            raise ValueError(f"Total score of all test cases must be 100, got {total}")
        return self

    @model_validator(mode="after")
    def validate_case_ids_unique(self) -> "Problem":
        ids = [tc.case_id for tc in self.test_cases]
        if len(ids) != len(set(ids)):
            raise ValueError("case_ids must be unique within a problem")
        return self

# Request/Response Models

class ProblemCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(..., min_length=1, max_length=100)
    description: str
    input_description: str
    output_description: str
    samples: List[Sample] = Field(..., min_length=1)
    constraints: Optional[str] = None
    time_limit: float = Field(gt=0)
    memory_limit: int = Field(gt=0)
    difficulty: str = Field(..., pattern=r"^(easy|medium|hard)$")
    tags: List[str] = Field(default_factory=list)
    test_cases: List[TestCase] = Field(..., min_length=1)

class ProblemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    input_description: Optional[str] = None
    output_description: Optional[str] = None
    samples: Optional[List[Sample]] = Field(None, min_length=1)
    constraints: Optional[str] = None
    time_limit: Optional[float] = Field(None, gt=0)
    memory_limit: Optional[int] = Field(None, gt=0)
    difficulty: Optional[str] = Field(None, pattern=r"^(easy|medium|hard)$")
    tags: Optional[List[str]] = None
    test_cases: Optional[List[TestCase]] = Field(None, min_length=1)

# Public View for students

class ProblemPublic(BaseModel):
    id: str
    title: str
    description: str
    input_description: str
    output_description: str
    samples: List[Sample]
    constraints: Optional[str]
    time_limit: float
    memory_limit: int
    difficulty: str
    tags: List[str]

    @classmethod
    def from_problem(cls, problem: Problem) -> "ProblemPublic":
        return cls(
            id=problem.id,
            title=problem.title,
            description=problem.description,
            input_description=problem.input_description,
            output_description=problem.output_description,
            samples=problem.samples,
            constraints=problem.constraints,
            time_limit=problem.time_limit,
            memory_limit=problem.memory_limit,
            difficulty=problem.difficulty,
            tags=problem.tags,
        )

class ProblemListResponse(BaseModel):
    id: str
    title: str
    difficulty: str
    tags: List[str]
    time_limit: float
    memory_limit: int