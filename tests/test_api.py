import pytest
import httpx
import time
import json

BASE_URL = "http://localhost:8000"

#  Test Data

STUDENT1_USERNAME = "pytest_student1"
STUDENT1_PASSWORD = "secure123456"

STUDENT2_USERNAME = "pytest_student2"
STUDENT2_PASSWORD = "secure123456"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

PROBLEM_ID = "P1001"
PROBLEM_DATA = {
    "id": PROBLEM_ID,
    "title": "A+B Problem",
    "description": "Input two integers and output their sum.",
    "input_description": "Two integers a and b on one line.",
    "output_description": "The sum of a and b.",
    "samples": [{"input": "1 2\n", "output": "3\n"}],
    "constraints": "|a|, |b| <= 10^9",
    "time_limit": 1.0,
    "memory_limit": 128,
    "difficulty": "easy",
    "tags": ["basic", "math"],
    "test_cases": [
        {"case_id": "case1", "input": "1 2\n", "output": "3\n", "score": 50, "is_hidden": False},
        {"case_id": "case2", "input": "-1 2\n", "output": "1\n", "score": 50, "is_hidden": True},
    ]
}

PROBLEM_DATA_INVALID_SCORE = {
    "id": "P9999",
    "title": "Invalid Score",
    "description": "Test",
    "input_description": "Test",
    "output_description": "Test",
    "samples": [{"input": "1\n", "output": "1\n"}],
    "constraints": "",
    "time_limit": 1.0,
    "memory_limit": 128,
    "difficulty": "easy",
    "tags": [],
    "test_cases": [
        {"case_id": "c1", "input": "1\n", "output": "1\n", "score": 80, "is_hidden": False},
        {"case_id": "c2", "input": "2\n", "output": "2\n", "score": 10, "is_hidden": False},  # total = 90 → invalid
    ]
}

CORRECT_CODE = "a, b = map(int, input().split())\nprint(a + b)\n"
WA_CODE = "print(0)\n"
RE_CODE = "print(1 / 0)\n"
TLE_CODE = "while True:\n    pass\n"
NORMALISATION_CODE = 'a, b = map(int, input().split())\nprint(a + b, " " * 3)\n'

SIMILAR_CODE_1 = "a, b = map(int, input().split())\nprint(a + b)\n"
SIMILAR_CODE_2 = "x, y = map(int, input().split())\nprint(x + y)\n"
DIFFERENT_CODE = 'print("hello")\n'


#  Fixtures & Helpers

@pytest.fixture(scope="session")
def client():
    """Persistent HTTP client with session support."""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c


def wait_for_submission(client, sub_id, timeout=15):
    """Poll a submission until it's finished or failed."""
    start = time.time()
    while time.time() - start < timeout:
        resp = client.get(f"/api/submissions/{sub_id}")
        if resp.status_code != 200:
            return None
        data = resp.json().get("data")
        if data and data.get("status") in ["finished", "failed"]:
            return data
        time.sleep(0.5)
    return None


def login(client, username, password):
    """Helper to log in and return the response."""
    return client.post("/api/auth/login", json={"username": username, "password": password})


def ensure_logged_in(client, username, password):
    """Log in and return the user data."""
    resp = login(client, username, password)
    assert resp.status_code == 200, f"Login failed for {username}"
    return resp.json().get("data")


def get_submission_id_from_result(client, username, password, problem_id, code, expected_result):
    """Submit code, wait for result, return submission ID and data."""
    login(client, username, password)
    resp = client.post(
        "/api/submissions",
        json={"problem_id": problem_id, "language": "python", "source_code": code}
    )
    assert resp.status_code == 202
    sub_id = resp.json()["data"]["submission_id"]
    result = wait_for_submission(client, sub_id)
    assert result is not None
    assert result["result"] == expected_result
    return sub_id, result


#  1. SERVER HEALTH

def test_server_alive(client):
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


#  2. AUTHENTICATION

def test_register_student1(client):
    resp = client.post("/api/auth/register", json={"username": STUDENT1_USERNAME, "password": STUDENT1_PASSWORD})
    assert resp.status_code in [201, 409]  # 409 means already exists


def test_register_student2(client):
    resp = client.post("/api/auth/register", json={"username": STUDENT2_USERNAME, "password": STUDENT2_PASSWORD})
    assert resp.status_code in [201, 409]


def test_login_student1(client):
    data = ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    assert data["role"] == "student"


def test_login_admin(client):
    data = ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    assert data["role"] == "admin"


def test_login_invalid_credentials(client):
    resp = login(client, STUDENT1_USERNAME, "wrongpassword")
    assert resp.status_code == 401
    # Should not reveal whether username or password is wrong
    assert "Invalid credentials" in resp.text


#  3. PROBLEM MANAGEMENT (Step 1)

def test_create_problem(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    
    # Delete the problem if it already exists
    client.delete(f"/api/problems/{PROBLEM_ID}")
    
    # create fresh
    resp = client.post("/api/problems", json=PROBLEM_DATA)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
    
    # verify test cases exist
    get_resp = client.get(f"/api/problems/{PROBLEM_ID}")
    assert get_resp.status_code == 200
    data = get_resp.json()["data"]
    assert "test_cases" in data
    assert len(data["test_cases"]) == 2

def test_duplicate_problem_id(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    resp = client.post("/api/problems", json=PROBLEM_DATA)
    assert resp.status_code == 409
    assert "already exists" in resp.text


def test_problem_invalid_score_sum(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    resp = client.post("/api/problems", json=PROBLEM_DATA_INVALID_SCORE)
    assert resp.status_code == 422
    assert "100" in resp.text  # error message mentions score total


def test_student_cannot_see_testcases(client):
    ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    resp = client.get(f"/api/problems/{PROBLEM_ID}")
    assert resp.status_code == 200
    data = resp.json().get("data")
    assert "test_cases" not in data


def test_admin_can_see_testcases(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    resp = client.get(f"/api/problems/{PROBLEM_ID}")
    assert resp.status_code == 200
    data = resp.json().get("data")
    assert "test_cases" in data
    assert len(data["test_cases"]) == 2


def test_update_problem(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    updated_title = "Updated A+B Problem"
    resp = client.put(
        f"/api/problems/{PROBLEM_ID}",
        json={"title": updated_title}
    )
    assert resp.status_code == 200
    data = resp.json().get("data")
    assert data["title"] == updated_title

    # Revert title so other tests don't break
    client.put(f"/api/problems/{PROBLEM_ID}", json={"title": "A+B Problem"})


def test_student_cannot_create_problem(client):
    ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    resp = client.post("/api/problems", json=PROBLEM_DATA)
    assert resp.status_code == 403


def test_student_cannot_update_problem(client):
    ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    resp = client.put(f"/api/problems/{PROBLEM_ID}", json={"title": "Hacked"})
    assert resp.status_code == 403


def test_student_cannot_delete_problem(client):
    ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    resp = client.delete(f"/api/problems/{PROBLEM_ID}")
    assert resp.status_code == 403


#  4. JUDGE / SUBMISSIONS (Step 2 & 4)

def test_submit_ac(client):
    sub_id, result = get_submission_id_from_result(
        client, STUDENT1_USERNAME, STUDENT1_PASSWORD,
        PROBLEM_ID, CORRECT_CODE, "AC"
    )
    assert result["score"] == 100


def test_submit_wa(client):
    sub_id, result = get_submission_id_from_result(
        client, STUDENT1_USERNAME, STUDENT1_PASSWORD,
        PROBLEM_ID, WA_CODE, "WA"
    )
    assert result["score"] == 0


def test_submit_re(client):
    sub_id, result = get_submission_id_from_result(
        client, STUDENT1_USERNAME, STUDENT1_PASSWORD,
        PROBLEM_ID, RE_CODE, "RE"
    )
    assert result["score"] == 0


def test_submit_tle(client):
    sub_id, result = get_submission_id_from_result(
        client, STUDENT1_USERNAME, STUDENT1_PASSWORD,
        PROBLEM_ID, TLE_CODE, "TLE"
    )
    assert result["score"] == 0


def test_output_normalisation_trailing_spaces(client):
    """Test that trailing spaces are normalised -> AC."""
    sub_id, result = get_submission_id_from_result(
        client, STUDENT1_USERNAME, STUDENT1_PASSWORD,
        PROBLEM_ID, NORMALISATION_CODE, "AC"
    )
    assert result["score"] == 100


def test_student_cannot_view_other_submission(client):
    # Student 1 submits AC code
    sub1_id, _ = get_submission_id_from_result(
        client, STUDENT1_USERNAME, STUDENT1_PASSWORD,
        PROBLEM_ID, CORRECT_CODE, "AC"
    )

    # Student 2 tries to view it -> 403
    ensure_logged_in(client, STUDENT2_USERNAME, STUDENT2_PASSWORD)
    resp = client.get(f"/api/submissions/{sub1_id}")
    assert resp.status_code == 403
    assert "own submissions" in resp.text


def test_empty_source_code_rejected(client):
    ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    resp = client.post(
        "/api/submissions",
        json={"problem_id": PROBLEM_ID, "language": "python", "source_code": ""}
    )
    assert resp.status_code == 422


def test_source_code_size_limit(client):
    ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    large_code = "a" * (64 * 1024 + 1)
    resp = client.post(
        "/api/submissions",
        json={"problem_id": PROBLEM_ID, "language": "python", "source_code": large_code}
    )
    assert resp.status_code == 422


#  5. LOGS & VISIBILITY (Step 5)

def test_student_logs_hide_hidden(client):
    # Get an AC submission from student1
    ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    list_resp = client.get("/api/submissions")
    ac_sub = next((s for s in list_resp.json()["data"]["items"] if s["result"] == "AC"), None)
    assert ac_sub is not None

    logs_resp = client.get(f"/api/submissions/{ac_sub['id']}/logs")
    assert logs_resp.status_code == 200
    logs = logs_resp.json().get("data")
    hidden_cases = [c for c in logs.get("cases", []) if c.get("is_hidden")]
    assert len(hidden_cases) == 0  # hidden cases removed


def test_admin_logs_show_hidden(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    list_resp = client.get("/api/submissions")
    ac_sub = next((s for s in list_resp.json()["data"]["items"] if s["result"] == "AC"), None)
    assert ac_sub is not None

    logs_resp = client.get(f"/api/submissions/{ac_sub['id']}/logs")
    assert logs_resp.status_code == 200
    logs = logs_resp.json().get("data")
    hidden_cases = [c for c in logs.get("cases", []) if c.get("is_hidden")]
    assert len(hidden_cases) > 0
    # Teacher sees input_data and expected_output
    case = hidden_cases[0]
    assert "input_data" in case
    assert "expected_output" in case


def test_teacher_can_search_all_logs(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    resp = client.get("/api/logs")
    assert resp.status_code == 200
    data = resp.json().get("data")
    assert "items" in data
    assert "total" in data


def test_student_cannot_search_all_logs(client):
    ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    resp = client.get("/api/logs")
    assert resp.status_code == 403


#  6. REJUDGE (Step 4)

def test_rejudge(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    list_resp = client.get("/api/submissions")
    ac_sub = next((s for s in list_resp.json()["data"]["items"] if s["result"] == "AC"), None)
    assert ac_sub is not None

    rej_resp = client.post(f"/api/submissions/{ac_sub['id']}/rejudge")
    assert rej_resp.status_code == 200
    result = wait_for_submission(client, ac_sub['id'])
    assert result is not None
    assert result["result"] == "AC"


def test_rejudge_pending_conflict(client):
    # Submit code and immediately try to rejudge while pending/running
    ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    resp = client.post(
        "/api/submissions",
        json={"problem_id": PROBLEM_ID, "language": "python", "source_code": TLE_CODE}
    )
    assert resp.status_code == 202
    sub_id = resp.json()["data"]["submission_id"]

    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    rej_resp = client.post(f"/api/submissions/{sub_id}/rejudge")
    # If still pending/running → 409; if finished (unlikely) → 200
    assert rej_resp.status_code in [409, 200]


#  7. AUDIT LOGS (Step 5)

def test_audit_logs_after_rejudge(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    list_resp = client.get("/api/submissions")
    ac_sub = next((s for s in list_resp.json()["data"]["items"] if s["result"] == "AC"), None)
    assert ac_sub is not None

    client.post(f"/api/submissions/{ac_sub['id']}/rejudge")
    wait_for_submission(client, ac_sub['id'])

    audit_resp = client.get("/api/audit-logs")
    assert audit_resp.status_code == 200
    events = [e for e in audit_resp.json()["data"]["items"] if e["action"] == "REJUDGE_SUBMISSION" and e["target_id"] == ac_sub["id"]]
    assert len(events) >= 1


def test_audit_logs_after_admin_view_logs(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    list_resp = client.get("/api/submissions")
    ac_sub = next((s for s in list_resp.json()["data"]["items"] if s["result"] == "AC"), None)
    assert ac_sub is not None

    client.get(f"/api/submissions/{ac_sub['id']}/logs")

    audit_resp = client.get("/api/audit-logs")
    events = [e for e in audit_resp.json()["data"]["items"] if e["action"] == "VIEW_FULL_JUDGE_LOG" and e["target_id"] == ac_sub["id"]]
    assert len(events) >= 1


#  8. USER MANAGEMENT (Step 3)

def test_admin_list_users(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    resp = client.get("/api/users")
    assert resp.status_code == 200
    data = resp.json().get("data")
    assert "items" in data
    assert data["total"] >= 3  # admin + 2 students


def test_admin_get_user(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    list_resp = client.get("/api/users")
    student = next((u for u in list_resp.json()["data"]["items"] if u["username"] == STUDENT1_USERNAME), None)
    assert student is not None

    resp = client.get(f"/api/users/{student['id']}")
    assert resp.status_code == 200
    data = resp.json().get("data")
    assert data["username"] == STUDENT1_USERNAME
    assert "password_hash" not in data


def test_admin_update_user_role(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    list_resp = client.get("/api/users")
    student = next((u for u in list_resp.json()["data"]["items"] if u["username"] == STUDENT1_USERNAME), None)
    assert student is not None

    resp = client.put(f"/api/users/{student['id']}", json={"role": "teacher"})
    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "teacher"

    # Revert to student
    client.put(f"/api/users/{student['id']}", json={"role": "student"})


def test_admin_cannot_disable_self(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    list_resp = client.get("/api/users")
    admin_user = next((u for u in list_resp.json()["data"]["items"] if u["username"] == ADMIN_USERNAME), None)
    assert admin_user is not None

    resp = client.put(f"/api/users/{admin_user['id']}", json={"is_active": False})
    assert resp.status_code == 400
    assert "Cannot disable your own account" in resp.text


def test_student_cannot_access_user_management(client):
    ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    resp = client.get("/api/users")
    assert resp.status_code == 403

    resp = client.get("/api/users/123")
    assert resp.status_code == 403

    resp = client.put("/api/users/123", json={"role": "teacher"})
    assert resp.status_code == 403


#  9. BACKUP & RESTORE (Step 6)

def test_create_backup(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    resp = client.post("/api/admin/backups")
    assert resp.status_code == 201
    data = resp.json().get("data")
    assert "backup_id" in data
    assert "created_at" in data


def test_list_backups(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    resp = client.get("/api/admin/backups")
    assert resp.status_code == 200
    data = resp.json().get("data")
    assert "items" in data
    assert data["total"] >= 1


def test_backup_restore(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)

    # Ensure the problem exists before backup
    client.post("/api/problems", json=PROBLEM_DATA) # safe if exists

    # Create fresh backup
    backup_resp = client.post("/api/admin/backups")
    assert backup_resp.status_code == 201
    backup_id = backup_resp.json()["data"]["backup_id"]

    # Delete problem
    del_resp = client.delete(f"/api/problems/{PROBLEM_ID}")
    assert del_resp.status_code == 200

    # Verify problem is gone
    get_resp = client.get(f"/api/problems/{PROBLEM_ID}")
    assert get_resp.status_code == 404

    # Restore from backup
    restore_resp = client.post(f"/api/admin/backups/{backup_id}/restore")
    assert restore_resp.status_code == 200

    # Verify problem is back
    get_resp2 = client.get(f"/api/problems/{PROBLEM_ID}")
    assert get_resp2.status_code == 200
    assert get_resp2.json()["data"]["id"] == PROBLEM_ID


#  10. ADV 3: SIMILARITY DETECTION

def test_adv3_submit_similar_codes(client):
    # Student 1 submits
    sub1_id, _ = get_submission_id_from_result(
        client, STUDENT1_USERNAME, STUDENT1_PASSWORD,
        PROBLEM_ID, SIMILAR_CODE_1, "AC"
    )
    # Student 2 submits (similar)
    sub2_id, _ = get_submission_id_from_result(
        client, STUDENT2_USERNAME, STUDENT2_PASSWORD,
        PROBLEM_ID, SIMILAR_CODE_2, "AC"
    )


def test_adv3_similarity_check(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    resp = client.post(f"/api/problems/{PROBLEM_ID}/similarity-check")
    assert resp.status_code == 200
    data = resp.json().get("data")
    assert data is not None
    pairs = data.get("pairs", [])
    # Should detect at least one pair between the two students
    assert len(pairs) >= 1
    assert pairs[0]["similarity"] >= 0.8


def test_adv3_get_similarity_report(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    resp = client.get(f"/api/problems/{PROBLEM_ID}/similarity-reports")
    assert resp.status_code == 200
    report = resp.json().get("data")
    assert report is not None
    assert report["problem_id"] == PROBLEM_ID
    assert len(report["pairs"]) >= 1


def test_adv3_similarity_access_denied_for_student(client):
    ensure_logged_in(client, STUDENT1_USERNAME, STUDENT1_PASSWORD)
    resp = client.post(f"/api/problems/{PROBLEM_ID}/similarity-check")
    assert resp.status_code == 403

    resp = client.get(f"/api/problems/{PROBLEM_ID}/similarity-reports")
    assert resp.status_code == 403


#  11. CLEANUP

def test_delete_problem_cleanup(client):
    ensure_logged_in(client, ADMIN_USERNAME, ADMIN_PASSWORD)
    resp = client.delete(f"/api/problems/{PROBLEM_ID}")
    assert resp.status_code in [200, 404]  # 404 if already deleted