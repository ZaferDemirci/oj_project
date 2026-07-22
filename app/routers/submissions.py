from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from typing import List, Optional
from datetime import datetime
import asyncio

from app.models.submission import (
    Submission, SubmissionCreate, SubmissionResponse,
    SubmissionFilters, SubmissionStatus, JudgeResult
)
from app.repositories.submission_repository import SubmissionRepository
from app.repositories.problem_repository import ProblemRepository
from app.utils.dependencies import get_current_user, require_teacher
from app.models.user import User
from app.judge.runner import run_judge
from app.repositories.audit_repository import AuditRepository
from app.models.audit import AuditLog

router = APIRouter()
submission_repo = SubmissionRepository()
problem_repo = ProblemRepository()


@router.post("/submissions", status_code=status.HTTP_202_ACCEPTED)
async def create_submission(
    submission_data: SubmissionCreate,
    request: Request,
    current_user: User = Depends(get_current_user)
) -> dict:
    # Check if problem exists
    problem = problem_repo.get_by_id(submission_data.problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Create submission record
    new_submission = Submission(
        user_id=current_user.id,
        problem_id=submission_data.problem_id,
        language=submission_data.language,
        source_code=submission_data.source_code,
        status="pending",
    )
    
    try:
        submission_repo.create(new_submission)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    
    # Start judge asynchronously
    asyncio.create_task(run_judge(new_submission.id))
    
    return {
        "code": status.HTTP_202_ACCEPTED,
        "message": "submission accepted",
        "data": {
            "submission_id": new_submission.id,
            "status": new_submission.status,
        }
    }


@router.get("/submissions")
async def get_submissions(
    request: Request,
    current_user: User = Depends(get_current_user),
    problem_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    status: Optional[SubmissionStatus] = Query(None),
    result: Optional[JudgeResult] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    """
    Students can only see their own submissions.
    Teachers and admins can see all submissions.
    """
    # Build filters
    filters = SubmissionFilters(
        problem_id=problem_id,
        user_id=user_id,
        status=status,
        result=result,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    
    # Permission: students can only query their own user_id
    if current_user.role == "student":
        # If the student specifies a different user_id, ignore it and force their own
        filters.user_id = current_user.id
    elif current_user.role in ["teacher", "admin"]:
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid role"
        )
    
    # Get all submissions (filtering is done in repository)
    all_submissions = submission_repo.get_all(filters)
    
    # Pagination
    total = len(all_submissions)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated = all_submissions[start_idx:end_idx]
    
    items = [SubmissionResponse.from_submission(s).model_dump() for s in paginated]
    
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    }


@router.get("/submissions/{submission_id}")
async def get_submission_detail(
    submission_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
) -> dict:
    """
    Students can only see their own submissions.
    Teachers/admins can see any submission.
    """
    submission = submission_repo.get_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Permission check
    if current_user.role == "student" and submission.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own submissions"
        )
    
    response_data = SubmissionResponse.from_submission(submission).model_dump()
    response_data["source_code"] = submission.source_code
    
    if current_user.role == "student":
        # remove judge_result (contains hidden test case details)
        response_data["judge_result"] = None
    else:
        response_data["judge_result"] = submission.judge_result
    
    return {
        "code": 200,
        "message": "ok",
        "data": response_data
    }


@router.post("/submissions/{submission_id}/rejudge")
async def rejudge_submission(
    submission_id: str,
    request: Request,
    current_user: User = Depends(require_teacher)
) -> dict:
    """
    Rerun the judge on an existing submission.
    Teachers and admins only.
    Only allowed for submissions in 'finished' or 'failed' state.
    """
    submission = submission_repo.get_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Check if the submission is in a state that can be rejudged
    if submission.status not in ["finished", "failed"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Submission is in '{submission.status}' state, cannot rejudge"
        )
    
    # Reset submission state to pending
    submission.status = "pending"
    submission.result = None
    submission.score = 0
    submission.total_time = None
    submission.started_at = None
    submission.finished_at = None
    submission.judge_result = None
    
    submission_repo.update(submission)
    
    # rejudge
    asyncio.create_task(run_judge(submission.id))
    audit_repo = AuditRepository()
    audit_log = AuditLog.create_log(
        operator_id=current_user.id,
        action="REJUDGE_SUBMISSION",
        target_type="submission",
        target_id=submission.id,
        success=True,
        detail=f"Rejudge triggered by {current_user.username}"
    )
    audit_repo.create(audit_log)
    return {
        "code": 200,
        "message": "Rejudge started successfully",
        "data": {
            "submission_id": submission.id,
            "status": submission.status,
        }
    }