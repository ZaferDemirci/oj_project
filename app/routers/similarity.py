from fastapi import APIRouter, Request, HTTPException, status, Depends
from app.utils.dependencies import require_teacher
from app.models.user import User
from app.repositories.submission_repository import SubmissionRepository
from app.repositories.problem_repository import ProblemRepository
from app.repositories.similarity_repository import SimilarityRepository
from app.services.similarity_service import find_similar_pairs

# Create router
router = APIRouter()

# Repositories
submission_repo = SubmissionRepository()
problem_repo = ProblemRepository()
similarity_repo = SimilarityRepository()


@router.post("/problems/{problem_id}/similarity-check")
async def check_similarity(
    problem_id: str,
    request: Request,
    current_user: User = Depends(require_teacher)) -> dict:
    try:
        # Check if problem exists
        problem = problem_repo.get_by_id(problem_id)
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )

        # Get all submissions for this problem (finished only)
        all_subs = submission_repo.get_by_problem_id(problem_id)
        submissions = []
        for sub in all_subs:
            if sub.status == "finished" and sub.source_code:
                submissions.append({
                    "id": sub.id,
                    "user_id": sub.user_id,
                    "source_code": sub.source_code,
                })

        if len(submissions) < 2:
            return {
                "code": 200,
                "message": "Not enough submissions to run similarity check",
                "data": {"pairs": [], "total_submissions": len(submissions)}
            }

        # Run similarity detection
        pairs = find_similar_pairs(submissions, threshold=0.8)

        # Save report
        report = {
            "problem_id": problem_id,
            "total_submissions": len(submissions),
            "pairs": pairs,
            "threshold": 0.8,
        }
        similarity_repo.save_report(problem_id, report)

        return {
            "code": 200,
            "message": "Similarity check completed",
            "data": {
                "pairs": pairs,
                "total_submissions": len(submissions),
                "threshold": 0.8,
            }
        }
    except Exception as e:
        print(f"Similarity check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Similarity check failed: {str(e)}"
        )


@router.get("/problems/{problem_id}/similarity-reports")
async def get_similarity_reports(
    problem_id: str,
    request: Request,
    current_user: User = Depends(require_teacher)
) -> dict:
    # Check if problem exists
    problem = problem_repo.get_by_id(problem_id)
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )

    report = similarity_repo.get_report(problem_id)
    if not report:
        return {
            "code": 200,
            "message": "No similarity reports found for this problem",
            "data": None
        }

    return {
        "code": 200,
        "message": "ok",
        "data": report
    }