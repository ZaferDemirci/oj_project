# Online Judge (OJ) System

## 1. Project Overview

### Project Goal

The goal of this project was to build a fully functional Online Judge (OJ) system using Python and FastAPI. The system supports user roles (student, teacher, admin), problem management, asynchronous code submission and judging, structured logging with role‑based visibility, backup/restore, and an optional code similarity detection module.

### Completed Features

* User registration, login, logout (Session‑based, bcrypt password hashing)
* Role‑based permissions (student, teacher, admin) with `is_active` support
* Problem CRUD (create, read, update, delete) with field validation and hidden test cases
* Asynchronous code submission (Python) using `asyncio.create_task`
* Multi‑testcase judging with subprocess isolation
* Detection of AC, WA, RE, TLE, SE
* Structured logs per test case, truncated and sanitised based on role
* Audit trails for sensitive actions (rejudge, view full logs, user updates, backup/restore)
* JSON persistence with atomic writes and error handling
* Admin backup/restore (with safety copies)
* Frontend (server‑side Jinja2 templates) for all required workflows
* Advanced Module 3: Code similarity detection (AST based)

### Incomplete Features

* No memory limit enforcement (MLE not implemented)
* No Special Judge (Adv 1) or Security Isolation (Adv 2)
* Only Python code is supported

### Persistence Method

**JSON files** are used for data storage. All data is stored in the `data/` directory, with separate files for users, problems, submissions, audit logs, and similarity reports. Atomic writes are implemented using temporary files and `os.replace()`.

### Advanced Modules Completed

* **Adv 3: Code Similarity Detection** – fully implemented (API + UI).

---

## 2. System Architecture

The system follows a layered architecture with clear separation of concerns.

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                          │
│  Jinja2 templates + static CSS (server‑side rendered)       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Routing Layer                         │
│  FastAPI routers: auth, problems, submissions, logs,        │
│  admin, users, similarity                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                           │
│  Business logic: similarity_service.py                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Repository Layer                         │
│  JSON file access with atomic I/O (BaseRepository)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Judge Layer                           │
│  executor (subprocess), comparator (output normalisation),  │
│  manager (multi‑testcase logic), runner (async task)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Utils Layer                           │
│  Dependencies (auth/permissions), password hashing,         │
│  sanitisation (truncation + path obfuscation),              │
│  admin initialisation                                       │
└─────────────────────────────────────────────────────────────┘
```

**Architecture Diagram (simplified):**

```
User Browser → FastAPI (Routers) → Services → Repositories → JSON Files
                  ↓
               Judge (async)
                  ↓
               Subprocess (student code)
```

* **Routing Layer**: FastAPI routers handle HTTP requests, apply permission dependencies, and delegate to services or repositories.
* **Service Layer**: Contains business logic (currently similarity service).
* **Repository Layer**: Abstracts data access; all file operations are atomic.
* **Judge Layer**: Manages subprocess execution, output normalisation, and result aggregation.
* **Utils Layer**: authentication, hashing, sanitisation.

The frontend is server‑side rendered with Jinja2 templates, so no separate frontend server is needed.

---

## 3. Data Design

All data is modelled with Pydantic and persisted as JSON.

### Main Models

**User**

```json
{
  "id": "uuid",
  "username": "string (3‑32 chars)",
  "password_hash": "bcrypt hash",
  "role": "student | teacher | admin",
  "is_active": true,
  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp"
}
```

**Problem**

```json
{
  "id": "string (1‑32, alnum_-)",
  "title": "string",
  "description": "string",
  "input_description": "string",
  "output_description": "string",
  "samples": [{"input": "...", "output": "..."}],
  "constraints": "string (optional)",
  "time_limit": float,
  "memory_limit": int,
  "difficulty": "easy | medium | hard",
  "tags": ["string"],
  "test_cases": [
    {
      "case_id": "string",
      "input": "string",
      "output": "string",
      "score": int,
      "is_hidden": bool
    }
  ]
}
```

**Submission**

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "problem_id": "string",
  "language": "python",
  "source_code": "string",
  "status": "pending | running | finished | failed",
  "result": "AC | WA | RE | TLE | SE | null",
  "score": int,
  "total_time": float (optional),
  "created_at": "ISO timestamp",
  "started_at": "ISO timestamp",
  "finished_at": "ISO timestamp",
  "judge_result": {
    "result": "...",
    "score": int,
    "total_time": float,
    "cases": [
      {
        "case_id": "string",
        "result": "...",
        "score": int,
        "time_used": float,
        "exit_code": int,
        "stdout": "string (truncated)",
        "stderr": "string (truncated)",
        "input_data": "string (truncated)",
        "expected_output": "string (truncated)",
        "is_hidden": bool
      }
    ]
  }
}
```

**AuditLog**

```json
{
  "id": "uuid",
  "operator_id": "uuid",
  "action": "VIEW_FULL_JUDGE_LOG | REJUDGE_SUBMISSION | UPDATE_USER_ROLE | DISABLE_USER | CREATE_BACKUP | RESTORE_BACKUP",
  "target_type": "submission | user | problem | backup",
  "target_id": "string (optional)",
  "success": bool,
  "detail": "string (optional)",
  "created_at": "ISO timestamp"
}
```

**Similarity Report** (stored in `similarity_reports.json` with key = problem_id)

```json
{
  "problem_id": "P1001",
  "total_submissions": 5,
  "threshold": 0.8,
  "pairs": [
    {
      "submission_a": "uuid",
      "submission_b": "uuid",
      "similarity": 0.87,
      "method": "ast"
    }
  ],
  "created_at": "ISO timestamp"
}
```

## 4. Core Implementation

### Asynchronous Judge

When a submission is created (`POST /api/submissions`), the endpoint returns HTTP 202 and the submission ID immediately. The judge is started as a background task using `asyncio.create_task(run_judge(submission.id))`.

*The `run_judge` coroutine (`app/judge/runner.py`) updates the submission status to `running`, invokes the judge (`app/judge/manager.py`), stores the structured result, and sets the status to `finished` or `failed`.

### Subprocess Execution & Termination

Each test case is executed in an isolated temporary directory using `asyncio.to_thread(subprocess.run)` in `app/judge/executor.py`. The subprocess runs the student's `main.py` with the test input via stdin. Timeout is enforced using the `timeout` parameter of `subprocess.run`. If the timeout expires, a `TimeoutExpired` exception is caught, and the test case is marked as TLE. The subprocess is automatically terminated by the timeout mechanism.

### Result Detection Logic

* **AC**: All test cases pass.
* **WA**: Program exits with 0 but output differs (after normalisation).
* **RE**: Program exits with nonzero exit code.
* **TLE**: Program exceeds the time limit.
* **SE**: Judge itself encounters an error (e.g., missing problem, invalid source).

Normalisation (newline, trailing spaces) is applied before comparison in `app/judge/comparator.py`.

### Output Normalisation

Implemented in `app/judge/comparator.py` (`normalize_output` and `compare_outputs`):

1. `\r\n` and `\r` → `\n`
2. Strip trailing spaces and tabs from each line
3. Remove trailing empty lines
4. Preserve leading spaces and internal spaces

### Permission Checks

Permissions are enforced at two levels:

* **Dependency injection** (`app/utils/dependencies.py`): `get_current_user` checks login, existence, and `is_active`; then `require_teacher` and `require_admin` check roles.
* **Endpoint logic** (`app/routers/`): Even if dependency passes, endpoints perform additional ownership checks (e.g., student cannot access others' submissions).

### Hidden Test Cases

* For students, the `ProblemPublic` model (`app/models/problem.py`) omits `test_cases` entirely.
* For logs, `sanitize_for_student` (`app/utils/sanitize.py`) removes any case with `is_hidden: true` and also strips `input_data` and `expected_output` from non‑hidden cases.

### Log Sanitisation & Truncation

* All log fields (`stdout`, `stderr`, `input_data`, `expected_output`) are truncated to 4000 characters before persistence using `truncate_text` (`app/utils/sanitize.py`).
* Absolute paths (Linux/Windows) are replaced with `<submission>/main.py` using `sanitize_paths` (`app/utils/sanitize.py`).

### Data Persistence & Atomic Writes

`BaseRepository` (`app/repositories/base.py`) provides `_load_data` (raises error on corruption) and `_save_data` (writes to temp file + `os.replace`). This ensures no partial writes and no silent data loss.

### Backup & Restore

* Backup (`app/routers/admin.py`): copies all JSON files to `data/backups/{timestamp}/` with a `manifest.json`.
* Restore (`app/routers/admin.py`): validates manifest, creates a safety copy of current data, then copies files from backup. If any error occurs during restore, the system reverts from the safety copy to maintain data integrity.

### Frontend Session Management

The frontend uses serverside sessions (Starlette `SessionMiddleware` configured in `app/main.py`). Upon login, `user_id` is stored in the session. Each page (`app/main.py`) checks the session to determine the current user and role. The frontend never stores passwords or tokens.

---

## 5. API Description

All endpoints are prefixed with `/api` and return `{code, message, data}`.

| Method | Endpoint | Permissions | Description |
|--------|----------|-------------|-------------|
| **Auth** (`app/routers/auth.py`) ||||
| POST | `/api/auth/register` | Public | Register new user (default student) |
| POST | `/api/auth/login` | Public | Login, sets session |
| POST | `/api/auth/logout` | Public (logged in) | Logout, clears session |
| GET | `/api/auth/me` | Logged in | Get current user info |
| **Users** (`app/routers/users.py`) ||||
| GET | `/api/users` | Admin | List users (paginated) |
| GET | `/api/users/{user_id}` | Admin | Get user details |
| PUT | `/api/users/{user_id}` | Admin | Update role/is_active (cannot disable self) |
| **Problems** (`app/routers/problems.py`) ||||
| GET | `/api/problems` | Logged in | List problems (public info) |
| GET | `/api/problems/{id}` | Logged in | Get problem; students see public, teachers full |
| POST | `/api/problems` | Teacher/Admin | Create problem (validates fields, score sum=100) |
| PUT | `/api/problems/{id}` | Teacher/Admin | Update problem (ID unchanged) |
| DELETE | `/api/problems/{id}` | Teacher/Admin | Delete problem |
| **Submissions** (`app/routers/submissions.py`) ||||
| POST | `/api/submissions` | Logged in, active | Submit code; returns 202 + submission_id |
| GET | `/api/submissions` | Logged in | List submissions with filters; students only own |
| GET | `/api/submissions/{id}` | Logged in | Get submission detail; students see own, teachers all |
| POST | `/api/submissions/{id}/rejudge` | Teacher/Admin | Re‑evaluate; only for finished/failed |
| **Logs** (`app/routers/logs.py`) ||||
| GET | `/api/submissions/{id}/logs` | Logged in | Get judge logs; student own only, teacher full |
| GET | `/api/logs` | Teacher/Admin | Search logs with filters |
| GET | `/api/audit-logs` | Admin | Filter audit logs |
| **Backup** (`app/routers/admin.py`) ||||
| POST | `/api/admin/backups` | Admin | Create backup |
| GET | `/api/admin/backups` | Admin | List backups |
| POST | `/api/admin/backups/{id}/restore` | Admin | Restore from backup |
| **Similarity (Adv 3)** (`app/routers/similarity.py`) ||||
| POST | `/api/problems/{id}/similarity-check` | Teacher/Admin | Run similarity detection |
| GET | `/api/problems/{id}/similarity-reports` | Teacher/Admin | Get saved report |

**Error Responses**:

* 400: Invalid request logic (e.g., admin disabling self)
* 401: Not logged in
* 403: Insufficient permissions
* 404: Resource not found
* 409: Conflict (duplicate, state conflict)
* 422: Validation error (Pydantic)
* 500: Internal server error

---

## 6. Test Results

All tests are written using `pytest` and `httpx` (`tests/test_api.py`). The suite runs 44 tests covering all mandatory features and the advanced similarity module.

### Summary

```
44 passed in 20.80s
```

### Key Test Areas

| Test Category | Included Tests | Status |
|---------------|----------------|--------|
| **Problem Management** | Create (valid, duplicate, invalid score), list, detail, update, delete; student cannot see test_cases; permission checks | All pass |
| **Judge** | AC, WA, RE, TLE, output normalisation (trailing spaces), empty source, source size limit | All pass |
| **Auth & Permissions** | Register (valid, duplicate, short password), login (valid, invalid, disabled), logout; student cannot access teacher endpoints; teacher cannot access admin endpoints | All pass |
| **Submissions** | Create, state transitions, student only own, teacher sees all, rejudge (valid and conflict), rejudge audit | All pass |
| **Logs** | Student logs hide hidden test cases, teacher logs show all, teacher log search, student cannot search, audit logs | All pass |
| **Backup & Restore** | Create backup, list, restore, delete problem and restore | All pass |
| **Similarity (Adv 3)** | Submit similar code, similarity check returns pairs, report retrieval, student access denied | All pass |
| **User Management** | Admin list, get, update role, cannot disable self; student access denied | All pass |

All tests run without any manual intervention (no mocking of external services). The server is started separately for the tests.

---

## 7. Problems and Solutions

### Problem 1: Atomic Writes & Data Corruption

**Issue**: During development, the repositories wrote directly to the JSON files. If a crash occurred during write, the file could become corrupted and the next `_load_data` would return an empty list/dict, silently erasing all data.

**Solution**:

* Introduced `BaseRepository` (`app/repositories/base.py`) with `_save_data` using a temporary file and `os.replace` for atomic writes.
* Modified `_load_data` to raise `RuntimeError` on `JSONDecodeError` instead of returning empty data.
* The API then returns a 500 error without wiping data.

### Problem 2: Missing Log Fields & Truncation

**Issue**: Initially, the judge result did not include `input_data` or `expected_output`; and logs were not truncated before persistence, leading to potential disk bloat.

**Solution**:

* Added `input_data` and `expected_output` to each test case result in `app/judge/manager.py`.
* Applied `truncate_text` (`app/utils/sanitize.py`) to all output fields (`stdout`, `stderr`, `input_data`, `expected_output`, and error messages) before storing them in the submission record.

### Problem 3: Server Reloads on `temp/` File Changes

**Issue**: Running `uvicorn` with `--reload` caused the server to restart every time the judge created a temporary file in `temp/`, killing the running subprocess and returning RE.

**Solution**:

* Used `--reload-dir app` to prevent the reloader from monitoring the `temp/` directory.
* For final testing, we run without `--reload`.

---

## 8. AI Tool Usage

### Tools Used

* **DeepSeek** - for debugging, architectural advice, general help (e.g. help configuring SessionMiddleware, AST) and writing test cases.
