import asyncio
from datetime import datetime
from app.judge import judge_submission
from app.repositories.submission_repository import SubmissionRepository
from app.repositories.problem_repository import ProblemRepository
from app.repositories.audit_repository import AuditRepository
from app.models.audit import AuditLog

submission_repo = SubmissionRepository()
problem_repo = ProblemRepository()
audit_repo = AuditRepository()


async def run_judge(submission_id: str):
    """
    Background task that runs the judge and updates the submission record.
    This runs asynchronously after the submission is created.
    """
    submission = None
    try:
        # Get submission
        submission = submission_repo.get_by_id(submission_id)
        if not submission:
            print(f"Submission {submission_id} not found during judge run")
            return

        # Get problem and test cases
        problem = problem_repo.get_by_id(submission.problem_id)
        if not problem:
            # Problem was deleted
            submission.status = "failed"
            submission.result = "SE"
            submission.finished_at = datetime.utcnow()
            submission_repo.update(submission)

            # Log the failure
            audit_log = AuditLog.create_log(
                operator_id=submission.user_id,
                action="JUDGE_FAILED",
                target_type="submission",
                target_id=submission.id,
                success=False,
                detail=f"Problem '{submission.problem_id}' not found during judge run"
            )
            audit_repo.create(audit_log)
            return

        # Update status to running
        submission.status = "running"
        submission.started_at = datetime.utcnow()
        submission_repo.update(submission)

        # Run the judge
        test_cases = [tc.model_dump() for tc in problem.test_cases]
        judge_output = await judge_submission(
            source_code=submission.source_code,
            test_cases=test_cases,
            time_limit=problem.time_limit,
        )

        # Update submission with results
        submission.status = "finished"
        submission.result = judge_output["result"]
        submission.score = judge_output["score"]
        submission.total_time = judge_output["total_time"]
        submission.judge_result = judge_output
        submission.finished_at = datetime.utcnow()
        submission_repo.update(submission)

        print(f"Submission {submission_id} finished with result {submission.result}")

        # Log successful judge completion
        audit_log = AuditLog.create_log(
            operator_id=submission.user_id,
            action="JUDGE_COMPLETED",
            target_type="submission",
            target_id=submission.id,
            success=True,
            detail=f"Judge finished with result {submission.result}, score {submission.score}"
        )
        audit_repo.create(audit_log)

    except Exception as e:
        # Any unexpected error -> mark as SE
        print(f"Judge runner error for submission {submission_id}: {e}")
        try:
            # Fetch submission again in case it was updated
            sub = submission_repo.get_by_id(submission_id) if submission_id else None
            if sub:
                sub.status = "failed"
                sub.result = "SE"
                sub.finished_at = datetime.utcnow()
                sub.judge_result = {
                    "result": "SE",
                    "score": 0,
                    "total_time": 0,
                    "cases": [],
                    "error": str(e),
                }
                submission_repo.update(sub)

                # Log system error
                audit_log = AuditLog.create_log(
                    operator_id=sub.user_id,
                    action="JUDGE_FAILED",
                    target_type="submission",
                    target_id=sub.id,
                    success=False,
                    detail=f"System Error during judge execution: {str(e)}"
                )
                audit_repo.create(audit_log)
            else:
                print(f"Could not update submission {submission_id} on error")
        except Exception as e2:
            print(f"Failed to update submission on error: {e2}")