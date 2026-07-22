from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from jinja2 import Environment, FileSystemLoader
import os
import asyncio
import json
from datetime import datetime
import httpx

# Import routers
from app.routers import auth, problems, submissions, logs, admin, similarity, users
from app.utils.init_admin import ensure_admin_exists
from app.utils.password import hash_password, verify_password

# Import repositories for frontend usage
from app.repositories.user_repository import UserRepository
from app.repositories.problem_repository import ProblemRepository
from app.repositories.submission_repository import SubmissionRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.similarity_repository import SimilarityRepository
from app.judge.runner import run_judge
from app.models.user import User
from app.models.submission import Submission
from app.models.audit import AuditLog
from app.models.problem import Problem
from app.utils.sanitize import sanitize_for_student, sanitize_for_teacher

# env
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# Session Middleware
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-dev-key-change-me") # DEV ONLY, MUST CHANGE IN PROD
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader("app/templates"),
    cache_size=0, # gave me errors
    auto_reload=True
)

# API Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(problems.router, prefix="/api", tags=["problems"])
app.include_router(submissions.router, prefix="/api", tags=["submissions"])
app.include_router(logs.router, prefix="/api", tags=["logs"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(similarity.router, prefix="/api", tags=["similarity"])
app.include_router(users.router, prefix="/api", tags=["users"])

# Repositories for frontend
user_repo = UserRepository()
problem_repo = ProblemRepository()
submission_repo = SubmissionRepository()
audit_repo = AuditRepository()
similarity_repo = SimilarityRepository()

# Helper to get current user from session
async def get_current_user_frontend(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        return None
    return user

# FRONTEND ROUTES

# Auth

@app.get("/login")
async def login_page(request: Request):
    user = await get_current_user_frontend(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    template = jinja_env.get_template("login.html")
    content = template.render(request=request)
    return HTMLResponse(content)

@app.post("/login")
async def login_post(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    user = user_repo.get_by_username(username)
    if not user or not user.is_active:
        template = jinja_env.get_template("login.html")
        content = template.render(request=request, error="Invalid credentials")
        return HTMLResponse(content, status_code=401)
    if not verify_password(password, user.password_hash):
        template = jinja_env.get_template("login.html")
        content = template.render(request=request, error="Invalid credentials")
        return HTMLResponse(content, status_code=401)
    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=302)

@app.get("/register")
async def register_page(request: Request):
    user = await get_current_user_frontend(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    template = jinja_env.get_template("register.html")
    content = template.render(request=request)
    return HTMLResponse(content)

@app.post("/register")
async def register_post(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    if len(username) < 3 or len(password) < 8:
        template = jinja_env.get_template("register.html")
        content = template.render(request=request, error="Username min 3, password min 8")
        return HTMLResponse(content, status_code=400)
    existing = user_repo.get_by_username(username)
    if existing:
        template = jinja_env.get_template("register.html")
        content = template.render(request=request, error="Username already exists")
        return HTMLResponse(content, status_code=409)
    hashed = hash_password(password)
    new_user = User(username=username, password_hash=hashed, role="student", is_active=True)
    user_repo.create(new_user)
    return RedirectResponse(url="/login", status_code=302)

@app.post("/logout")
async def logout_post(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

# Home
@app.get("/")
async def home(request: Request):
    user = await get_current_user_frontend(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    problems = problem_repo.get_all()
    template = jinja_env.get_template("home.html")
    content = template.render(request=request, user=user, problems=problems)
    return HTMLResponse(content)

@app.get("/problems")
async def problems_redirect():
    return RedirectResponse(url="/", status_code=302)

# Teacher/Admin: Create Problem
@app.get("/problems/create")
async def create_problem_page(request: Request):
    user = await get_current_user_frontend(request)
    if not user or user.role not in ["teacher", "admin"]:
        return RedirectResponse(url="/", status_code=302)
    template = jinja_env.get_template("create_problem.html")
    content = template.render(request=request, user=user, is_edit=False)
    return HTMLResponse(content)

@app.post("/problems/create")
async def create_problem_post(request: Request):
    user = await get_current_user_frontend(request)
    if not user or user.role not in ["teacher", "admin"]:
        return RedirectResponse(url="/", status_code=302)
    form = await request.form()
    try:
        problem_data = {
            "id": form.get("id"),
            "title": form.get("title"),
            "description": form.get("description"),
            "input_description": form.get("input_description"),
            "output_description": form.get("output_description"),
            "samples": json.loads(form.get("samples")),
            "constraints": form.get("constraints"),
            "time_limit": float(form.get("time_limit")),
            "memory_limit": int(form.get("memory_limit")),
            "difficulty": form.get("difficulty"),
            "tags": [t.strip() for t in form.get("tags", "").split(",") if t.strip()],
            "test_cases": json.loads(form.get("test_cases"))
        }
        new_problem = Problem(**problem_data)
        problem_repo.create(new_problem)
    except Exception as e:
        return RedirectResponse(url="/problems/create?error=invalid", status_code=302)
    return RedirectResponse(url="/", status_code=302)

# Teacher/Admin: Edit Problem
@app.get("/problems/{problem_id}/edit")
async def edit_problem_page(request: Request, problem_id: str):
    user = await get_current_user_frontend(request)
    if not user or user.role not in ["teacher", "admin"]:
        return RedirectResponse(url="/", status_code=302)
    
    problem = problem_repo.get_by_id(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Convert Pydantic models to JSON strings for template
    samples_json = json.dumps([s.model_dump() for s in problem.samples])
    test_cases_json = json.dumps([tc.model_dump() for tc in problem.test_cases])
    
    template = jinja_env.get_template("create_problem.html")
    content = template.render(
        request=request,
        user=user,
        problem=problem,
        samples_json=samples_json,
        test_cases_json=test_cases_json,
        is_edit=True
    )
    return HTMLResponse(content)

@app.post("/problems/{problem_id}/edit")
async def edit_problem_post(request: Request, problem_id: str):
    user = await get_current_user_frontend(request)
    if not user or user.role not in ["teacher", "admin"]:
        return RedirectResponse(url="/", status_code=302)
    
    existing = problem_repo.get_by_id(problem_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    form = await request.form()
    try:
        problem_data = {
            "id": problem_id,
            "title": form.get("title"),
            "description": form.get("description"),
            "input_description": form.get("input_description"),
            "output_description": form.get("output_description"),
            "samples": json.loads(form.get("samples")),
            "constraints": form.get("constraints"),
            "time_limit": float(form.get("time_limit")),
            "memory_limit": int(form.get("memory_limit")),
            "difficulty": form.get("difficulty"),
            "tags": [t.strip() for t in form.get("tags", "").split(",") if t.strip()],
            "test_cases": json.loads(form.get("test_cases"))
        }
        updated_problem = Problem(**problem_data)
        problem_repo.update(updated_problem)
    except Exception as e:
        return RedirectResponse(url=f"/problems/{problem_id}/edit?error=invalid", status_code=302)
    return RedirectResponse(url=f"/problems/{problem_id}", status_code=302)

# Problem Detail
@app.get("/problems/{problem_id}")
async def problem_detail(request: Request, problem_id: str):
    user = await get_current_user_frontend(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    problem = problem_repo.get_by_id(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    template = jinja_env.get_template("problem_detail.html")
    content = template.render(
        request=request,
        user=user,
        problem=problem,
        is_teacher=user.role in ["teacher", "admin"]
    )
    return HTMLResponse(content)

@app.post("/problems/{problem_id}/submit")
async def submit_code(request: Request, problem_id: str):
    user = await get_current_user_frontend(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    form = await request.form()
    source_code = form.get("source_code")
    if not source_code or not source_code.strip():
        return RedirectResponse(url=f"/problems/{problem_id}?error=empty_code", status_code=302)
    problem = problem_repo.get_by_id(problem_id)
    if not problem:
        return RedirectResponse(url="/", status_code=302)
    new_sub = Submission(
        user_id=user.id,
        problem_id=problem_id,
        language="python",
        source_code=source_code,
        status="pending"
    )
    submission_repo.create(new_sub)
    asyncio.create_task(run_judge(new_sub.id))
    return RedirectResponse(url=f"/submissions/{new_sub.id}", status_code=302)

@app.post("/problems/{problem_id}/delete")
async def delete_problem_post(request: Request, problem_id: str):
    user = await get_current_user_frontend(request)
    if not user or user.role not in ["teacher", "admin"]:
        return RedirectResponse(url="/", status_code=302)
    problem_repo.delete(problem_id)
    return RedirectResponse(url="/", status_code=302)

# Submissions
@app.get("/submissions")
async def submissions_list(request: Request):
    user = await get_current_user_frontend(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    all_subs = submission_repo.get_all()
    if user.role not in ["teacher", "admin"]:
        all_subs = [s for s in all_subs if s.user_id == user.id]
    
    # Sorted list of (submission, username) tuples
    submission_list = []
    for sub in all_subs:
        sub_user = user_repo.get_by_id(sub.user_id)
        username = sub_user.username if sub_user else "Unknown"
        submission_list.append((sub, username))
    
    # Sort by created_at descending
    submission_list.sort(key=lambda t: t[0].created_at, reverse=True)
    
    template = jinja_env.get_template("submissions.html")
    content = template.render(request=request, user=user, submissions=submission_list)
    return HTMLResponse(content)

@app.get("/submissions/{submission_id}")
async def submission_detail(request: Request, submission_id: str):
    user = await get_current_user_frontend(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    sub = submission_repo.get_by_id(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if user.role == "student" and sub.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your submission")
    
    # Get username for submitter
    sub_user = user_repo.get_by_id(sub.user_id)
    submitter_username = sub_user.username if sub_user else "Unknown"
    
    logs = sub.judge_result
    if logs:
        if user.role == "student":
            logs = sanitize_for_student(logs)
        else:
            logs = sanitize_for_teacher(logs)
    
    template = jinja_env.get_template("submission_detail.html")
    content = template.render(
        request=request,
        user=user,
        submission=sub,
        logs=logs,
        is_teacher=user.role in ["teacher", "admin"],
        submitter_username=submitter_username
    )
    return HTMLResponse(content)

@app.post("/submissions/{submission_id}/rejudge")
async def rejudge_post(request: Request, submission_id: str):
    user = await get_current_user_frontend(request)
    if not user or user.role not in ["teacher", "admin"]:
        return RedirectResponse(url="/", status_code=302)
    sub = submission_repo.get_by_id(submission_id)
    if not sub:
        return RedirectResponse(url="/submissions", status_code=302)
    if sub.status not in ["finished", "failed"]:
        return RedirectResponse(url=f"/submissions/{submission_id}?error=cannot_rejudge", status_code=302)
    
    # Reset submission
    sub.status = "pending"
    sub.result = None
    sub.score = 0
    sub.total_time = None
    sub.started_at = None
    sub.finished_at = None
    sub.judge_result = None
    submission_repo.update(sub)
    
    # Write audit log
    audit_log = AuditLog.create_log(
        operator_id=user.id,
        action="REJUDGE_SUBMISSION",
        target_type="submission",
        target_id=submission_id,
        success=True,
        detail=f"Rejudge triggered by {user.username}"
    )
    audit_repo.create(audit_log)
    
    asyncio.create_task(run_judge(sub.id))
    return RedirectResponse(url=f"/submissions/{submission_id}", status_code=302)

# Admin: Backups
@app.get("/admin/backups")
async def admin_backups(request: Request):
    user = await get_current_user_frontend(request)
    if not user or user.role != "admin":
        return RedirectResponse(url="/", status_code=302)
    import os
    import json
    backup_dir = "data/backups"
    backups = []
    if os.path.exists(backup_dir):
        for item in os.listdir(backup_dir):
            path = os.path.join(backup_dir, item)
            if os.path.isdir(path):
                manifest_path = os.path.join(path, "manifest.json")
                if os.path.exists(manifest_path):
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)
                        backups.append(manifest)
                else:
                    backups.append({"backup_id": item, "created_at": "unknown", "files": []})
    template = jinja_env.get_template("admin_backups.html")
    content = template.render(request=request, user=user, backups=backups)
    return HTMLResponse(content)

@app.post("/admin/backups/create")
async def create_backup_post(request: Request):
    user = await get_current_user_frontend(request)
    if not user or user.role != "admin":
        return RedirectResponse(url="/", status_code=302)
    import shutil
    import json
    import os
    from datetime import datetime
    backup_id = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    backup_path = os.path.join("data/backups", backup_id)
    os.makedirs(backup_path, exist_ok=True)
    manifest = {"backup_id": backup_id, "created_at": datetime.utcnow().isoformat() + "Z", "files": []}
    for filename in os.listdir("data"):
        if filename.endswith(".json") and filename != "backups":
            src = os.path.join("data", filename)
            dst = os.path.join(backup_path, filename)
            shutil.copy2(src, dst)
            manifest["files"].append(filename)
    with open(os.path.join(backup_path, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return RedirectResponse(url="/admin/backups", status_code=302)

@app.post("/admin/backups/{backup_id}/restore")
async def restore_backup_post(request: Request, backup_id: str):
    user = await get_current_user_frontend(request)
    if not user or user.role != "admin":
        return RedirectResponse(url="/", status_code=302)
    import shutil
    import json
    import os
    backup_path = os.path.join("data/backups", backup_id)
    if not os.path.exists(backup_path):
        return RedirectResponse(url="/admin/backups?error=notfound", status_code=302)
    manifest_path = os.path.join(backup_path, "manifest.json")
    if not os.path.exists(manifest_path):
        return RedirectResponse(url="/admin/backups?error=invalid", status_code=302)
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    for filename in manifest.get("files", []):
        src = os.path.join(backup_path, filename)
        dst = os.path.join("data", filename)
        if os.path.exists(src):
            shutil.copy2(src, dst)
    return RedirectResponse(url="/admin/backups?success=restored", status_code=302)

# Admin: User Management
@app.get("/admin/users")
async def admin_users_list(request: Request):
    user = await get_current_user_frontend(request)
    if not user or user.role != "admin":
        return RedirectResponse(url="/", status_code=302)
    
    all_users = user_repo.get_all()
    all_users.sort(key=lambda u: u.username)
    
    content = jinja_env.get_template("admin_users.html").render(
        request=request,
        user=user,
        users=all_users
    )
    return HTMLResponse(content)

@app.get("/admin/users/{user_id}")
async def admin_user_edit(request: Request, user_id: str):
    current_user = await get_current_user_frontend(request)
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/", status_code=302)
    
    target_user = user_repo.get_by_id(user_id)
    if not target_user:
        return RedirectResponse(url="/admin/users?error=notfound", status_code=302)
    
    content = jinja_env.get_template("admin_user_edit.html").render(
        request=request,
        user=current_user,
        target_user=target_user
    )
    return HTMLResponse(content)

@app.post("/admin/users/{user_id}")
async def admin_user_update(request: Request, user_id: str):
    current_user = await get_current_user_frontend(request)
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/", status_code=302)
    
    target_user = user_repo.get_by_id(user_id)
    if not target_user:
        return RedirectResponse(url="/admin/users?error=notfound", status_code=302)
    
    # Prevent admin from modifying their own account
    if user_id == current_user.id:
        return RedirectResponse(url=f"/admin/users/{user_id}?error=self_modify", status_code=302)
    
    form = await request.form()
    role = form.get("role")
    is_active = form.get("is_active") == "true"
    
    if role not in ["student", "teacher", "admin"]:
        return RedirectResponse(url=f"/admin/users/{user_id}?error=invalid_role", status_code=302)
    
    target_user.role = role
    target_user.is_active = is_active
    user_repo.update(target_user)
    
    audit_log = AuditLog.create_log(
        operator_id=current_user.id,
        action="UPDATE_USER_ROLE",
        target_type="user",
        target_id=user_id,
        success=True,
        detail=f"Updated user {target_user.username} role={role}, is_active={is_active}"
    )
    audit_repo.create(audit_log)
    
    return RedirectResponse(url="/admin/users?success=updated", status_code=302)

# Similarity (Frontend)
@app.post("/problems/{problem_id}/similarity-check")
async def similarity_check_post(request: Request, problem_id: str):
    user = await get_current_user_frontend(request)
    if not user or user.role not in ["teacher", "admin"]:
        return RedirectResponse(url="/", status_code=302)
    
    from app.services.similarity_service import find_similar_pairs
    from app.repositories.submission_repository import SubmissionRepository
    
    # Get all finished submissions for this problem
    sub_repo = SubmissionRepository()
    all_subs = sub_repo.get_by_problem_id(problem_id)
    
    submissions = []
    for sub in all_subs:
        if sub.status == "finished" and sub.source_code:
            submissions.append({
                "id": sub.id,
                "user_id": sub.user_id,
                "source_code": sub.source_code,
            })
    
    if len(submissions) < 2:
        # Redirect, but show a message
        return RedirectResponse(
            url=f"/problems/{problem_id}/similarity-reports?error=not_enough",
            status_code=302
        )
    
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
    
    # Redirect to the report page
    return RedirectResponse(
        url=f"/problems/{problem_id}/similarity-reports?success=checked",
        status_code=302
    )


@app.get("/problems/{problem_id}/similarity-reports")
async def similarity_report_page(request: Request, problem_id: str):
    user = await get_current_user_frontend(request)
    if not user or user.role not in ["teacher", "admin"]:
        return RedirectResponse(url="/", status_code=302)
    
    problem = problem_repo.get_by_id(problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    report = similarity_repo.get_report(problem_id)
    
    # Enrich report with usernames
    enriched_pairs = []
    if report and report.get("pairs"):
        for pair in report["pairs"]:
            sub_a = submission_repo.get_by_id(pair["submission_a"])
            sub_b = submission_repo.get_by_id(pair["submission_b"])
            
            user_a = user_repo.get_by_id(sub_a.user_id) if sub_a else None
            user_b = user_repo.get_by_id(sub_b.user_id) if sub_b else None
            
            enriched_pairs.append({
                "submission_a": pair["submission_a"],
                "submission_b": pair["submission_b"],
                "username_a": user_a.username if user_a else "Unknown",
                "username_b": user_b.username if user_b else "Unknown",
                "similarity": pair["similarity"],
                "method": pair.get("method", "ast"),
            })
        report["pairs"] = enriched_pairs
    
    # Render template
    template = jinja_env.get_template("problem_detail.html")
    content = template.render(
        request=request,
        user=user,
        problem=problem,
        is_teacher=True,
        similarity_report=report
    )
    return HTMLResponse(content)


# Health Check
@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    ensure_admin_exists()