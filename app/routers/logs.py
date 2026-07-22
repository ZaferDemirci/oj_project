from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from typing import Optional
from datetime import datetime
import traceback

from app.utils.dependencies import get_current_user, require_teacher, require_admin
from app.models.user import User
from app.repositories.submission_repository import SubmissionRepository
from app.repositories.audit_repository import AuditRepository
from app.models.audit import AuditLog
from app.utils.sanitize import sanitize_for_student, sanitize_for_teacher, truncate_text

router = APIRouter()
submission_repo = SubmissionRepository()
audit_repo = AuditRepository()


@router.get("/submissions/{submission_id}/logs")
async def get_submission_logs(
    submission_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)) -> dict:
    """
    Get logs for a specific submission.
    - Student: sees own submission, non-hidden test cases only, sanitized.
    - Teacher/Admin: sees all test cases, full logs (still truncated).
    """
    submission = submission_repo.get_by_id(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    # Permission: student can only view their own
    if current_user.role == "student" and submission.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own submission logs"
        )
    
    judge_result = submission.judge_result
    if not judge_result:
        return {
            "code": 200,
            "message": "No judge logs available yet",
            "data": None
        }
    
    # Role-based sanitization
    if current_user.role == "student":
        sanitized = sanitize_for_student(judge_result)
    else:
        # Teacher/Admin: get full logs
        sanitized = sanitize_for_teacher(judge_result)
        # Log audit event for teacher/admin viewing full logs
        audit_log = AuditLog.create_log(
            operator_id=current_user.id,
            action="VIEW_FULL_JUDGE_LOG",
            target_type="submission",
            target_id=submission_id,
            success=True,
            detail=f"Viewed logs for submission {submission_id}"
        )
        audit_repo.create(audit_log)
    
    return {
        "code": 200,
        "message": "ok",
        "data": sanitized
    }


@router.get("/logs")
async def get_all_logs(
    request: Request,
    current_user: User = Depends(require_teacher),
    submission_id: Optional[str] = Query(None),
    problem_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    result: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),) -> dict:
    try:
        # Get all submissions
        all_subs = submission_repo.get_all()
        
        # Apply filters manually
        filtered = []
        for sub in all_subs:
            # Only finished submissions have logs
            if sub.status not in ["finished","failed"]:
                continue
            if submission_id and sub.id != submission_id:
                continue
            if problem_id and sub.problem_id != problem_id:
                continue
            if user_id and sub.user_id != user_id:
                continue
            if result and sub.result != result:
                continue
            if start_time and sub.created_at < start_time:
                continue
            if end_time and sub.created_at > end_time:
                continue
            # Only include submissions with judge_result
            if not sub.judge_result:
                continue
            filtered.append(sub)
        
        # Sort by created_at descending (newest first)
        filtered.sort(key=lambda s: s.created_at, reverse=True)
        
        # Paginate
        total = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = filtered[start_idx:end_idx]
        
        items = []
        for sub in paginated:
            # Ensure judge_result is dict
            judge_result = sub.judge_result
            if not isinstance(judge_result, dict):
                # If not dict, treat as empty
                judge_result = {}
            sanitized = sanitize_for_teacher(judge_result)
            items.append({
                "submission_id": sub.id,
                "user_id": sub.user_id,
                "problem_id": sub.problem_id,
                "result": sub.result,
                "score": sub.score,
                "created_at": sub.created_at,
                "logs": sanitized,
            })
        
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
    except Exception as e:
        # Print full traceback to server log for debugging
        print("=" * 60)
        print("ERROR in GET /api/logs:")
        traceback.print_exc()
        print("=" * 60)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/audit-logs")
async def get_audit_logs(
    request: Request,
    current_user: User = Depends(require_admin),
    operator_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),) -> dict:
    filters = {
        "operator_id": operator_id,
        "action": action,
        "target_id": target_id,
        "start_time": start_time,
        "end_time": end_time,
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    logs = audit_repo.get_all(filters)
    total = len(logs)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated = logs[start_idx:end_idx]
    
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "items": [l.model_dump() for l in paginated],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    }