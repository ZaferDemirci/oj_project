from fastapi import APIRouter, Request, HTTPException, status, Depends
from typing import List
from pydantic import ValidationError
from app.models.problem import (
    Problem, ProblemCreate, ProblemUpdate, 
    ProblemPublic, ProblemListResponse
)
from app.repositories.problem_repository import ProblemRepository
from app.utils.dependencies import get_current_user, require_teacher
from app.models.user import User

router = APIRouter()
problem_repo = ProblemRepository()


# Public endpoints

@router.get("/problems")
async def get_problems(
    request: Request,
    current_user: User = Depends(get_current_user)
) -> dict:
    problems = problem_repo.get_all()
    items = [
        ProblemListResponse(
            id=p.id,
            title=p.title,
            difficulty=p.difficulty,
            tags=p.tags,
            time_limit=p.time_limit,
            memory_limit=p.memory_limit
        ).model_dump()
        for p in problems
    ]
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "items": items,
            "total": len(items),
            "page": 1,
            "page_size": len(items) if items else 20
        }
    }


@router.get("/problems/{problem_id}")
async def get_problem_detail(
    problem_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
) -> dict:
    problem = problem_repo.get_by_id(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if current_user.role in ["teacher", "admin"]:
        data = problem.model_dump()
    else:
        data = ProblemPublic.from_problem(problem).model_dump()
    return {"code": 200, "message": "ok", "data": data}


# Protected endpoints (teachers/admins only)

@router.post("/problems", status_code=status.HTTP_201_CREATED)
async def create_problem(
    problem_data: ProblemCreate,
    current_user: User = Depends(require_teacher)
) -> dict:
    # Check duplicate ID (409)
    if problem_repo.exists(problem_data.id):
        raise HTTPException(
            status_code=409,
            detail=f"Problem with id '{problem_data.id}' already exists"
        )
    
    # Validate and build Problem (catch Pydantic errors for 422)
    try:
        new_problem = Problem(**problem_data.model_dump())
    except ValidationError as e:
        # Convert Pydantic validation errors to HTTP 422
        raise HTTPException(status_code=422, detail=str(e))
    
    # Save
    problem_repo.create(new_problem)
    return {
        "code": 201,
        "message": "Problem created successfully",
        "data": new_problem.model_dump()
    }


@router.put("/problems/{problem_id}")
async def update_problem(
    problem_id: str,
    update_data: ProblemUpdate,
    current_user: User = Depends(require_teacher)
) -> dict:
    existing = problem_repo.get_by_id(problem_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Merge updates
    updated_dict = existing.model_dump()
    for key, value in update_data.model_dump(exclude_unset=True).items():
        if value is not None:
            updated_dict[key] = value
    
    # Validate merged data
    try:
        updated_problem = Problem(**updated_dict)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    problem_repo.update(updated_problem)
    return {
        "code": 200,
        "message": "Problem updated successfully",
        "data": updated_problem.model_dump()
    }


@router.delete("/problems/{problem_id}")
async def delete_problem(
    problem_id: str,
    current_user: User = Depends(require_teacher)
) -> dict:
    if not problem_repo.exists(problem_id):
        raise HTTPException(status_code=404, detail="Problem not found")
    problem_repo.delete(problem_id)
    return {"code": 200, "message": "Problem deleted successfully", "data": None}